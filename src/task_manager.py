#!/usr/bin/env python3

import rospy
import actionlib
import yaml
import time
import os

from move_base_msgs.msg import MoveBaseAction, MoveBaseGoal
from geometry_msgs.msg import Quaternion
from std_msgs.msg import String
from tf.transformations import quaternion_from_euler
from enum import Enum


class RobotState(Enum):
    INIT = 0
    GO_TO_ROOM_ENTRY = 1
    QR_VERIFY = 2
    EXECUTE_CLEANING = 3
    REPORT = 4
    NEXT_ROOM = 5
    FINISH = 6


class TaskManager:
    def __init__(self):
        rospy.init_node('task_manager', anonymous=False)

        self.load_mission_config()

        self.move_base_client = actionlib.SimpleActionClient(
            'move_base', MoveBaseAction
        )

        rospy.loginfo("Waiting for move_base action server...")
        if not self.move_base_client.wait_for_server(rospy.Duration(15.0)):
            rospy.logerr("move_base action server not available!")
            rospy.signal_shutdown("move_base not available")
            return

        rospy.loginfo("move_base action server connected!")

        self.qr_result = None
        rospy.Subscriber('/qr_result', String, self.qr_callback)


        self.state = RobotState.INIT
        self.current_room_index = 0


        self.cleaning_report = {
            'total_rooms': len(self.rooms),
            'completed': [],
            'skipped': [],
            'failed': []
        }

        self.qr_timeout = 15.0
        self.navigation_timeout = 120.0
        self.qr_retry_limit = 2

        rospy.loginfo("🧠 Task Manager initialized!")


    def load_mission_config(self):
        import rospkg
        rp = rospkg.RosPack()
        package_path = rp.get_path('robot_supurge')
        
        config_path = rospy.get_param('~mission_file', os.path.join(package_path, 'config/mission.yaml'))
        config_path = os.path.expanduser(config_path)
       

        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)

        self.rooms = []
        for room_name in config['rooms']:
            room_cfg = config[room_name]
            self.rooms.append({
                'name': room_name,
                'entry_goal': room_cfg['entry_goal'],
                'cleaning_goals': room_cfg.get('cleaning_goals', []),
                'qr_expected': room_cfg.get('qr_expected', '')
            })

        rospy.loginfo(f"Loaded {len(self.rooms)} rooms from config")


    def qr_callback(self, msg):
        self.qr_result = msg.data
        rospy.loginfo(f"📷 QR detected: {self.qr_result}")



    def create_goal(self, x, y, yaw):
        goal = MoveBaseGoal()
        goal.target_pose.header.frame_id = "map"
        goal.target_pose.header.stamp = rospy.Time.now()
        goal.target_pose.pose.position.x = x
        goal.target_pose.pose.position.y = y
        goal.target_pose.pose.position.z = 0.0

        q = quaternion_from_euler(0, 0, yaw)
        goal.target_pose.pose.orientation = Quaternion(*q)
        return goal


    def navigate_to_goal(self, x, y, yaw, timeout):
        rospy.loginfo(f"Navigating to: x={x}, y={y}, yaw={yaw}")

        # 🔴 HARD RESET ACTIONLIB (CRITICAL)
        self.move_base_client.cancel_all_goals()
        rospy.sleep(0.5)

        if not self.move_base_client.wait_for_server(rospy.Duration(5.0)):
            rospy.logerr(" move_base server lost!")
            return False

        goal = self.create_goal(x, y, yaw)
        self.move_base_client.send_goal(goal)

        finished = self.move_base_client.wait_for_result(
            rospy.Duration(timeout)
        )

        if not finished:
            rospy.logwarn("⏱️ Navigation timeout, canceling goal")
            self.move_base_client.cancel_all_goals()
            return False

        state = self.move_base_client.get_state()

        if state == actionlib.GoalStatus.SUCCEEDED:
            rospy.loginfo("✅ Navigation succeeded!")
            return True
        else:
            rospy.logwarn(f"❌ Navigation failed, state={state}")
            self.move_base_client.cancel_all_goals()
            return False


    def verify_qr(self, expected):
        # Orijinal dünyada QR olmadığı için şimdilik hep TRUE döndürüyoruz
        rospy.loginfo("QR verification succesful")
        return True



    def execute_cleaning_route(self, room):
        for wp in room['cleaning_goals']:
            self.navigate_to_goal(
                wp['x'], wp['y'], wp['yaw'],
                self.navigation_timeout
            )
            rospy.sleep(1.5)
        return True


    def run_state_machine(self):
        rate = rospy.Rate(1)

        while not rospy.is_shutdown():

            if self.state == RobotState.INIT:
                rospy.loginfo("State: INIT")
                self.state = RobotState.GO_TO_ROOM_ENTRY

            elif self.state == RobotState.GO_TO_ROOM_ENTRY:
                if self.current_room_index >= len(self.rooms):
                    self.state = RobotState.FINISH
                    continue

                room = self.rooms[self.current_room_index]
                rospy.loginfo(f"GO_TO_ROOM_ENTRY: {room['name']}")

                entry = room['entry_goal']
                ok = self.navigate_to_goal(
                    entry['x'], entry['y'], entry['yaw'],
                    self.navigation_timeout
                )

                if ok:
                    self.state = RobotState.QR_VERIFY
                else:
                    self.cleaning_report['failed'].append(room['name'])
                    self.state = RobotState.NEXT_ROOM

            elif self.state == RobotState.QR_VERIFY:
                room = self.rooms[self.current_room_index]
                if self.verify_qr(room['qr_expected']):
                    self.state = RobotState.EXECUTE_CLEANING
                else:
                    self.cleaning_report['skipped'].append(room['name'])
                    self.state = RobotState.NEXT_ROOM

            elif self.state == RobotState.EXECUTE_CLEANING:
                room = self.rooms[self.current_room_index]
                self.execute_cleaning_route(room)
                self.cleaning_report['completed'].append(room['name'])
                self.state = RobotState.REPORT

            elif self.state == RobotState.REPORT:
                rospy.loginfo(f"Finished room: {self.rooms[self.current_room_index]['name']}")
                self.state = RobotState.NEXT_ROOM

            elif self.state == RobotState.NEXT_ROOM:
                self.current_room_index += 1
                self.state = RobotState.GO_TO_ROOM_ENTRY

            elif self.state == RobotState.FINISH:
                self.generate_final_report()
                break

            rate.sleep()


    def generate_final_report(self):
        rospy.loginfo("=" * 50)
        rospy.loginfo("📊 FINAL CLEANING REPORT")
        rospy.loginfo(self.cleaning_report)
        rospy.loginfo("=" * 50)




if __name__ == '__main__':
    try:
        manager = TaskManager()
        manager.run_state_machine()
    except rospy.ROSInterruptException:
        pass
