# 🧹 Süpürge Robotu: Oda Bazlı Temizlik ve QR Doğrulama

Bu proje, **KTÜN Robotiğe Giriş Dersi** final ödevi kapsamında geliştirilmiştir. Proje, bir TurtleBot3 robotunun Gazebo ortamında otonom haritalama yapmasını, belirlenen odalara giderek QR kodlar aracılığıyla konumunu doğrulamasını ve her oda için temizlik rotalarını tamamlamasını amaçlar.

---

##  Gereksinimler ve Kurulum

### 1. Sistem Gereksinimleri
* **Ubuntu 20.04** & **ROS Noetic**
* **TurtleBot3** Paketleri
* **Python 3** (pyzbar ve opencv-python kütüphaneleri)

### 2. Kütüphane Kurulumu
Terminale aşağıdaki komutları yazarak gerekli bağımlılıkları yükleyin:
```bash
sudo apt-get install ros-noetic-turtlebot3*
pip3 install pyzbar opencv-python
```

---

## 📂 Dosya Yapısı
robot_supurge/
├── config/
│   └── mission.yaml          
├── launch/
│   ├── sim.launch            
│   ├── slam.launch           
│   ├── navigation.launch     
│   └── task_manager.launch   
├── maps/
│   ├── ev_haritasi.yaml      
│   └── ev_haritasi.pgm       
├── world/      
│   ├── models/           
│        ├── qr_bedroom          
│        ├── qr_corridor     
│        ├── qr_kitchen 
│        └── qr_livingroom        
├── src/
│   ├── qr_reader.py          
│   └── task_manager.py       
├── world/
│   └── turtlebot3_house_qr.world 
└── README.md

---

## 🚀 Çalıştırma Adımları

### 1. Aşama: Haritalama (SLAM)
Robotu manuel gezdirerek haritayı oluşturun:
```bash
roslaunch robot_supurge sim.launch
roslaunch robot_supurge slam.launch
rosrun turtlebot3_teleop turtlebot3_teleop_key.launch
# Haritayı kaydetmek için:
rosrun map_server map_saver -f ~/robotik_ws/src/robot_supurge/maps/ev_haritasi
```

### 2. Aşama: Otonom Görev (Navigasyon ve Temizlik)
Harita hazır olduktan sonra görev yöneticisini başlatın:
```bash
# Simülasyonu başlat
roslaunch robot_supurge sim.launch
# Navigasyonu başlat
roslaunch robot_supurge navigation.launch
# Görev Yöneticisini başlat
roslaunch robot_supurge task_manager.launch
```

---

## 🧠 Durum Makinesi (FSM) Akışı
Program şu aşamaları takip eder:
1. **INIT**: Navigasyon sunucusuna bağlanır.
2. **GO_TO_ROOM_ENTRY**: Odanın giriş kapısına gider.
3. **QR_VERIFY**: Kamera ile QR kodu okur ve odayı doğrular.
4. **EXECUTE_CLEANING**: Oda içindeki temizlik rotasını tamamlar.
5. **REPORT**: Sonuçları raporlar ve bir sonraki odaya geçer.

---



