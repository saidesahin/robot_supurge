#!/usr/bin/env python3
import rospy
from sensor_msgs.msg import Image
from std_msgs.msg import String
from cv_bridge import CvBridge
import cv2
from pyzbar import pyzbar

class QRReader:
    def __init__(self):
        rospy.init_node("qr_reader")

        self.bridge = CvBridge()
        self.qr_pub = rospy.Publisher("/qr/result", String, queue_size=10)

        rospy.Subscriber(
            "/camera/rgb/image_raw",
            Image,
            self.image_callback
        )

        rospy.loginfo("📷 QR Reader Started")

    def image_callback(self, msg):
        try:
            frame = self.bridge.imgmsg_to_cv2(msg, "bgr8")
        except:
            return

        decoded_objects = pyzbar.decode(frame)

        for obj in decoded_objects:
            qr_data = obj.data.decode("utf-8")
            rospy.loginfo(f"🔍 QR OKUNDU: {qr_data}")
            self.qr_pub.publish(qr_data)
            return  

if __name__ == "__main__":
    QRReader()
    rospy.spin()
