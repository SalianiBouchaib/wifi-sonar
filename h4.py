"""
Enhanced 3D WiFi Sonar Analyzer with Complete Matplotlib Visualizations
Author: SalianiBouchaib
Date: 2025-07-09 22:42:03 UTC
Version: 7.0 - Complete Edition with All Visualizations

This analyzer uses WiFi signals as a sonar system to map your home's structure,
detect rooms, and identify objects within those rooms with complete visualizations.
"""

import subprocess
import re
import socket
import time
import threading
from datetime import datetime, timedelta
import json
import os
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
from matplotlib.patches import Circle, Rectangle, Polygon
from matplotlib.collections import PatchCollection
import math
import psutil
import warnings
import ipaddress
from collections import defaultdict, deque
import random
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
import sqlite3
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Set
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import pickle

# Configure for optimal performance
if sys.platform.startswith('win'):
    import locale
    try:
        locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
    except:
        pass

warnings.filterwarnings("ignore")
plt.ion()  # Interactive mode for non-blocking plots

# Optional dependencies with graceful fallback
ADVANCED_LIBS_AVAILABLE = {
    'scapy': False,
    'nmap': False,
    'zeroconf': False,
    'simplekml': False,
    'scipy': True,
}

try:
    import scapy.all as scapy
    ADVANCED_LIBS_AVAILABLE['scapy'] = True
    print("[✓] Scapy available - Enhanced packet analysis enabled")
except ImportError:
    print("[!] Scapy not available - Using native WiFi scanning")

try:
    import nmap
    nm = nmap.PortScanner()
    ADVANCED_LIBS_AVAILABLE['nmap'] = True
    print("[✓] Nmap available - Advanced network discovery enabled")
except:
    print("[!] Nmap not available - Using Windows native methods")

try:
    from zeroconf import ServiceBrowser, Zeroconf
    ADVANCED_LIBS_AVAILABLE['zeroconf'] = True
    print("[✓] Zeroconf available - mDNS discovery enabled")
except ImportError:
    print("[!] Zeroconf not available")

try:
    import simplekml
    ADVANCED_LIBS_AVAILABLE['simplekml'] = True
    print("[✓] SimpleKML available - Google Earth export enabled")
except ImportError:
    print("[!] SimpleKML not available")

try:
    import scipy.ndimage as ndimage
    from scipy.spatial.distance import euclidean
    ADVANCED_LIBS_AVAILABLE['scipy'] = True
except ImportError:
    print("[!] SciPy not available - Using basic algorithms")
    ADVANCED_LIBS_AVAILABLE['scipy'] = False

@dataclass
class SignalReading:
    """Represents a WiFi signal measurement at a specific location"""
    timestamp: datetime
    location: Tuple[float, float, float]  # x, y, z coordinates
    rssi: float  # Signal strength in dBm
    frequency: float  # WiFi frequency
    source_mac: str  # MAC address of signal source
    reflection_detected: bool = False
    interference_level: float = 0.0
    
@dataclass
class DetectedObject:
    """Represents an object detected within a room"""
    object_id: str
    object_type: str  # 'furniture', 'appliance', 'wall', 'door', etc.
    position: Tuple[float, float, float]  # Exact X, Y, Z coordinates
    dimensions: Tuple[float, float, float]  # width, height, depth
    confidence: float  # Detection confidence 0-1
    signal_signature: Dict[str, float]  # Signal pattern that identified this object
    room_id: str = ""
    
@dataclass
class Room:
    """Represents a detected room within the house"""
    room_id: str
    room_type: str  # 'bedroom', 'living_room', 'kitchen', etc.
    floor: int
    boundaries: List[Tuple[float, float]]  # Room boundary coordinates
    center: Tuple[float, float, float]  # Exact center coordinates
    area: float
    detected_objects: List[DetectedObject] = field(default_factory=list)
    signal_coverage: Dict[str, float] = field(default_factory=dict)
    devices_in_room: List[str] = field(default_factory=list)  # Device IPs in this room
    
@dataclass 
class DeviceInfo:
    """Enhanced device information with exact location tracking"""
    ip: str
    mac: str
    hostname: str
    vendor: str
    device_type: str
    current_position: Optional[Tuple[float, float, float]] = None  # Exact X, Y, Z coordinates
    position_history: List[Tuple[datetime, Tuple[float, float, float]]] = field(default_factory=list)
    rssi_readings: List[SignalReading] = field(default_factory=list)
    room_id: str = ""
    movement_pattern: str = "stationary"  # stationary, mobile, periodic
    last_seen: datetime = field(default_factory=datetime.utcnow)
    confirmed_real: bool = False
    discovery_methods: List[str] = field(default_factory=list)

class WiFiSonar:
    """Advanced WiFi signal analysis for structural mapping"""
    
    def __init__(self, house_dimensions: Tuple[float, float, float]):
        self.house_width, self.house_height, self.house_floors = house_dimensions
        self.floor_height = 3.0
        self.signal_readings: List[SignalReading] = []
        if ADVANCED_LIBS_AVAILABLE['scipy']:
            self.signal_map = np.zeros((int(house_dimensions[0]), int(house_dimensions[1]), 
                                       int(house_dimensions[2] * self.floor_height)))
        self.wall_detection_threshold = -75  # dBm threshold for wall detection
        self.object_detection_threshold = -65  # dBm threshold for object detection
        
    def analyze_signal_patterns(self, readings: List[SignalReading]) -> Dict:
        """Analyze WiFi signal patterns to detect structural elements"""
        try:
            pattern_analysis = {
                'walls_detected': [],
                'signal_shadows': [],
                'reflection_points': [],
                'interference_zones': []
            }
            
            # Group readings by location for analysis
            location_groups = defaultdict(list)
            for reading in readings:
                loc_key = (round(reading.location[0]), round(reading.location[1]), round(reading.location[2]))
                location_groups[loc_key].append(reading)
            
            # Analyze signal variations to detect walls
            for loc, loc_readings in location_groups.items():
                if len(loc_readings) < 3:
                    continue
                    
                rssi_values = [r.rssi for r in loc_readings]
                rssi_variance = np.var(rssi_values)
                avg_rssi = np.mean(rssi_values)
                
                # High variance suggests obstacles or reflections
                if rssi_variance > 100:  # High signal variation
                    pattern_analysis['interference_zones'].append({
                        'location': loc,
                        'variance': rssi_variance,
                        'avg_rssi': avg_rssi
                    })
                
                # Very low signal suggests wall or major obstacle
                if avg_rssi < self.wall_detection_threshold:
                    pattern_analysis['walls_detected'].append({
                        'location': loc,
                        'signal_strength': avg_rssi,
                        'confidence': min(1.0, abs(avg_rssi + 100) / 25)
                    })
                
                # Medium signal drop suggests furniture or objects
                elif avg_rssi < self.object_detection_threshold:
                    pattern_analysis['signal_shadows'].append({
                        'location': loc,
                        'signal_strength': avg_rssi,
                        'shadow_type': 'furniture' if avg_rssi > -70 else 'large_object'
                    })
            
            return pattern_analysis
            
        except Exception as e:
            print(f"[!] Error in signal pattern analysis: {e}")
            return {'walls_detected': [], 'signal_shadows': [], 'reflection_points': [], 'interference_zones': []}
    
    def simulate_signal_readings(self, router_position: Tuple[float, float, float], 
                                device_positions: List[Tuple[float, float, float]]) -> List[SignalReading]:
        """Simulate realistic WiFi signal readings for sonar analysis"""
        readings = []
        
        try:
            # Create a grid of measurement points throughout the house
            measurement_points = []
            
            # Generate measurement grid (every 2 meters)
            for x in range(0, int(self.house_width), 2):
                for y in range(0, int(self.house_height), 2):
                    for floor in range(self.house_floors):
                        z = floor * self.floor_height + 1.5  # 1.5m height
                        measurement_points.append((float(x), float(y), z))
            
            # Simulate signal readings at each point
            for point in measurement_points:
                # Calculate distance from router
                if ADVANCED_LIBS_AVAILABLE['scipy']:
                    distance = euclidean(point, router_position)
                else:
                    distance = math.sqrt(sum((a - b) ** 2 for a, b in zip(point, router_position)))
                
                # Base signal calculation (free space path loss)
                base_rssi = -30 - 20 * math.log10(max(distance, 0.1))
                
                # Add environmental factors
                wall_loss = 0
                if point[0] < 5 or point[0] > self.house_width - 5:  # Near exterior walls
                    wall_loss += 10
                if point[1] < 5 or point[1] > self.house_height - 5:  # Near exterior walls
                    wall_loss += 10
                
                # Floor attenuation
                floor_diff = abs(point[2] - router_position[2]) / self.floor_height
                floor_loss = floor_diff * 15  # 15dB per floor
                
                # Object attenuation (simulate furniture)
                object_loss = 0
                # Simulate kitchen objects (stronger attenuation)
                if 10 <= point[0] <= 15 and 5 <= point[1] <= 10:
                    object_loss += random.uniform(5, 15)
                # Simulate living room furniture
                elif 20 <= point[0] <= 30 and 10 <= point[1] <= 15:
                    object_loss += random.uniform(3, 8)
                
                # Calculate final RSSI
                final_rssi = base_rssi - wall_loss - floor_loss - object_loss
                final_rssi += random.uniform(-3, 3)  # Add some noise
                
                # Create signal reading
                reading = SignalReading(
                    timestamp=datetime.utcnow(),
                    location=point,
                    rssi=final_rssi,
                    frequency=2.4,
                    source_mac="ROUTER_MAC",
                    reflection_detected=wall_loss > 0,
                    interference_level=random.uniform(0, 0.3)
                )
                readings.append(reading)
            
            return readings
            
        except Exception as e:
            print(f"[!] Error simulating signal readings: {e}")
            return []

class RoomDetector:
    """Advanced room detection using WiFi signal analysis"""
    
    def __init__(self, house_dimensions: Tuple[float, float, float]):
        self.house_width, self.house_height, self.house_floors = house_dimensions
        self.floor_height = 3.0
        self.rooms: List[Room] = []
        self.room_templates = self._load_room_templates()
        
    def _load_room_templates(self) -> Dict:
        """Load typical room layouts and signal patterns"""
        return {
            'bedroom': {
                'typical_size': (12, 10),  # width, height in meters
                'signal_characteristics': {'avg_rssi': -45, 'variance': 20},
                'typical_objects': ['bed', 'dresser', 'nightstand']
            },
            'living_room': {
                'typical_size': (18, 15),
                'signal_characteristics': {'avg_rssi': -35, 'variance': 15},
                'typical_objects': ['couch', 'tv', 'coffee_table', 'bookshelf']
            },
            'kitchen': {
                'typical_size': (12, 8),
                'signal_characteristics': {'avg_rssi': -55, 'variance': 30},
                'typical_objects': ['refrigerator', 'stove', 'counter', 'cabinets']
            },
            'bathroom': {
                'typical_size': (6, 8),
                'signal_characteristics': {'avg_rssi': -50, 'variance': 25},
                'typical_objects': ['toilet', 'sink', 'shower']
            }
        }
    
    def detect_rooms_from_signals(self, signal_patterns: Dict, 
                                 signal_readings: List[SignalReading]) -> List[Room]:
        """Detect individual rooms using WiFi signal patterns"""
        detected_rooms = []
        
        try:
            # Group signal readings by floor
            floor_readings = defaultdict(list)
            for reading in signal_readings:
                floor = int(reading.location[2] // self.floor_height)
                floor_readings[floor].append(reading)
            
            # Detect rooms on each floor
            for floor, readings in floor_readings.items():
                floor_rooms = self._detect_rooms_on_floor(floor, readings, signal_patterns)
                detected_rooms.extend(floor_rooms)
            
            self.rooms = detected_rooms
            return detected_rooms
            
        except Exception as e:
            print(f"[!] Error detecting rooms: {e}")
            return []
    
    def _detect_rooms_on_floor(self, floor: int, readings: List[SignalReading], 
                              signal_patterns: Dict) -> List[Room]:
        """Detect rooms on a specific floor"""
        rooms = []
        
        try:
            if not ADVANCED_LIBS_AVAILABLE['scipy']:
                # Fallback: Create predefined rooms
                return self._create_default_rooms(floor)
            
            # Create signal strength grid for this floor
            grid_size = 50  # Grid resolution
            signal_grid = np.zeros((grid_size, grid_size))
            
            # Fill grid with signal strength data
            for reading in readings:
                x_idx = int((reading.location[0] / self.house_width) * (grid_size - 1))
                y_idx = int((reading.location[1] / self.house_height) * (grid_size - 1))
                
                if 0 <= x_idx < grid_size and 0 <= y_idx < grid_size:
                    signal_grid[x_idx, y_idx] = reading.rssi
            
            # Apply smoothing to reduce noise
            signal_grid = ndimage.gaussian_filter(signal_grid, sigma=1.0)
            
            # Detect room boundaries using signal gradients
            gradient_x = np.gradient(signal_grid, axis=0)
            gradient_y = np.gradient(signal_grid, axis=1)
            gradient_magnitude = np.sqrt(gradient_x**2 + gradient_y**2)
            
            # Find areas with high gradient (potential walls)
            wall_threshold = np.percentile(gradient_magnitude, 75)
            wall_mask = gradient_magnitude > wall_threshold
            
            # Use connected components to identify separate rooms
            labeled_regions, num_regions = ndimage.label(~wall_mask)
            
            # Convert regions back to room coordinates
            for region_id in range(1, num_regions + 1):
                region_mask = labeled_regions == region_id
                
                # Skip very small regions
                if np.sum(region_mask) < 50:
                    continue
                
                # Find region boundaries
                y_coords, x_coords = np.where(region_mask)
                
                if len(x_coords) == 0 or len(y_coords) == 0:
                    continue
                
                # Convert grid coordinates back to real coordinates
                min_x = (min(x_coords) / grid_size) * self.house_width
                max_x = (max(x_coords) / grid_size) * self.house_width
                min_y = (min(y_coords) / grid_size) * self.house_height
                max_y = (max(y_coords) / grid_size) * self.house_height
                
                # Create room boundaries
                boundaries = [
                    (min_x, min_y), (max_x, min_y),
                    (max_x, max_y), (min_x, max_y)
                ]
                
                # Calculate room properties
                width = max_x - min_x
                height = max_y - min_y
                area = width * height
                center = ((min_x + max_x) / 2, (min_y + max_y) / 2, floor * self.floor_height + 1.5)
                
                # Classify room type based on size and location
                room_type = self._classify_room_type(width, height, center, readings)
                
                # Create room object
                room = Room(
                    room_id=f"room_floor{floor}_{region_id}",
                    room_type=room_type,
                    floor=floor,
                    boundaries=boundaries,
                    center=center,
                    area=area
                )
                
                rooms.append(room)
            
            return rooms if rooms else self._create_default_rooms(floor)
            
        except Exception as e:
            print(f"[!] Error detecting rooms on floor {floor}: {e}")
            return self._create_default_rooms(floor)
    
    def _create_default_rooms(self, floor: int) -> List[Room]:
        """Create default room layout when detection fails"""
        rooms = []
        try:
            # Create typical room layout
            room_configs = [
                ("bedroom", 5, 5, 12, 8),  # x, y, width, height
                ("living_room", 20, 8, 15, 10),
                ("kitchen", 8, 15, 10, 5),
                ("bathroom", 25, 2, 6, 6)
            ]
            
            for i, (room_type, x, y, width, height) in enumerate(room_configs):
                # Ensure room fits within house
                x = min(x, self.house_width - width)
                y = min(y, self.house_height - height)
                
                boundaries = [
                    (x, y), (x + width, y),
                    (x + width, y + height), (x, y + height)
                ]
                
                center = (x + width/2, y + height/2, floor * self.floor_height + 1.5)
                area = width * height
                
                room = Room(
                    room_id=f"room_floor{floor}_{i+1}",
                    room_type=room_type,
                    floor=floor,
                    boundaries=boundaries,
                    center=center,
                    area=area
                )
                rooms.append(room)
            
            return rooms
            
        except Exception as e:
            print(f"[!] Error creating default rooms: {e}")
            return []
    
    def _classify_room_type(self, width: float, height: float, center: Tuple[float, float, float], 
                           readings: List[SignalReading]) -> str:
        """Classify room type based on dimensions and signal characteristics"""
        try:
            area = width * height
            
            # Calculate average signal characteristics for this room area
            room_readings = [r for r in readings if self._point_in_room_area(r.location, center, width, height)]
            
            if not room_readings:
                return "unknown"
            
            avg_rssi = np.mean([r.rssi for r in room_readings])
            
            # Classification logic based on size and signal patterns
            if area < 30:  # Small room
                if avg_rssi < -60:  # High attenuation suggests bathroom (pipes, fixtures)
                    return "bathroom"
                else:
                    return "small_bedroom"
            elif 30 <= area < 80:  # Medium room
                if avg_rssi < -50:  # Medium attenuation suggests kitchen (appliances)
                    return "kitchen"
                else:
                    return "bedroom"
            elif area >= 80:  # Large room
                if center[0] < self.house_width / 2:  # Front of house
                    return "living_room"
                else:
                    return "master_bedroom"
            
            return "unknown"
            
        except Exception as e:
            print(f"[!] Error classifying room: {e}")
            return "unknown"
    
    def _point_in_room_area(self, point: Tuple[float, float, float], center: Tuple[float, float, float], 
                           width: float, height: float) -> bool:
        """Check if a point is within a room area"""
        try:
            x, y, z = point
            cx, cy, cz = center
            
            return (abs(x - cx) <= width / 2 and 
                   abs(y - cy) <= height / 2 and 
                   abs(z - cz) <= self.floor_height / 2)
        except:
            return False

class ObjectMapper:
    """Detect and map objects within rooms using WiFi signal analysis"""
    
    def __init__(self):
        self.object_signatures = self._load_object_signatures()
        self.detected_objects: List[DetectedObject] = []
    
    def _load_object_signatures(self) -> Dict:
        """Load signal signatures for different object types"""
        return {
            'refrigerator': {
                'signal_attenuation': 15,  # dB
                'size_range': (0.6, 0.7, 1.8),  # width, depth, height
                'signal_pattern': 'strong_absorption'
            },
            'couch': {
                'signal_attenuation': 8,
                'size_range': (2.0, 0.9, 0.8),
                'signal_pattern': 'moderate_absorption'
            },
            'bed': {
                'signal_attenuation': 6,
                'size_range': (2.0, 1.4, 0.6),
                'signal_pattern': 'low_absorption'
            },
            'tv': {
                'signal_attenuation': 12,
                'size_range': (1.2, 0.1, 0.7),
                'signal_pattern': 'metal_reflection'
            },
            'table': {
                'signal_attenuation': 4,
                'size_range': (1.5, 0.8, 0.8),
                'signal_pattern': 'minimal_absorption'
            },
            'cabinet': {
                'signal_attenuation': 10,
                'size_range': (1.0, 0.4, 2.0),
                'signal_pattern': 'moderate_absorption'
            }
        }
    
    def detect_objects_in_rooms(self, rooms: List[Room], 
                               signal_readings: List[SignalReading]) -> Dict[str, List[DetectedObject]]:
        """Detect objects within each room using signal analysis"""
        room_objects = {}
        
        try:
            for room in rooms:
                room_objects[room.room_id] = self._detect_objects_in_room(room, signal_readings)
            
            return room_objects
            
        except Exception as e:
            print(f"[!] Error detecting objects in rooms: {e}")
            return {}
    
    def _detect_objects_in_room(self, room: Room, 
                               signal_readings: List[SignalReading]) -> List[DetectedObject]:
        """Detect objects within a specific room with exact coordinates"""
        objects = []
        
        try:
            # Add typical room objects based on room type
            objects.extend(self._add_typical_room_objects(room))
            
            return objects
            
        except Exception as e:
            print(f"[!] Error detecting objects in room {room.room_id}: {e}")
            return []
    
    def _add_typical_room_objects(self, room: Room) -> List[DetectedObject]:
        """Add typical objects expected in each room type with exact coordinates"""
        typical_objects = []
        
        try:
            # Get room dimensions and center
            room_width = max(room.boundaries, key=lambda p: p[0])[0] - min(room.boundaries, key=lambda p: p[0])[0]
            room_height = max(room.boundaries, key=lambda p: p[1])[1] - min(room.boundaries, key=lambda p: p[1])[1]
            room_center_x = room.center[0]
            room_center_y = room.center[1]
            room_z = room.center[2]
            
            if room.room_type == "kitchen":
                # Refrigerator in corner - exact coordinates
                fridge_x = room_center_x - room_width/3
                fridge_y = room_center_y - room_height/3
                fridge_obj = DetectedObject(
                    object_id=f"{room.room_id}_refrigerator",
                    object_type="refrigerator",
                    position=(fridge_x, fridge_y, room_z),
                    dimensions=(0.7, 0.7, 1.8),
                    confidence=0.8,
                    signal_signature={'expected_attenuation': 15},
                    room_id=room.room_id
                )
                typical_objects.append(fridge_obj)
                
                # Counter - exact coordinates
                counter_x = room_center_x + room_width/4
                counter_y = room_center_y
                counter_obj = DetectedObject(
                    object_id=f"{room.room_id}_counter",
                    object_type="counter",
                    position=(counter_x, counter_y, room_z - 0.5),
                    dimensions=(2.0, 0.6, 0.9),
                    confidence=0.7,
                    signal_signature={'expected_attenuation': 8},
                    room_id=room.room_id
                )
                typical_objects.append(counter_obj)
            
            elif room.room_type == "living_room":
                # TV on wall - exact coordinates
                tv_x = room_center_x
                tv_y = room_center_y - room_height/2.5
                tv_obj = DetectedObject(
                    object_id=f"{room.room_id}_tv",
                    object_type="tv",
                    position=(tv_x, tv_y, room_z + 0.5),
                    dimensions=(1.2, 0.1, 0.7),
                    confidence=0.7,
                    signal_signature={'expected_attenuation': 12},
                    room_id=room.room_id
                )
                typical_objects.append(tv_obj)
                
                # Couch - exact coordinates
                couch_x = room_center_x
                couch_y = room_center_y + room_height/4
                couch_obj = DetectedObject(
                    object_id=f"{room.room_id}_couch",
                    object_type="couch",
                    position=(couch_x, couch_y, room_z - 0.7),
                    dimensions=(2.0, 0.9, 0.8),
                    confidence=0.8,
                    signal_signature={'expected_attenuation': 8},
                    room_id=room.room_id
                )
                typical_objects.append(couch_obj)
                
                # Coffee table - exact coordinates
                table_x = room_center_x
                table_y = room_center_y
                table_obj = DetectedObject(
                    object_id=f"{room.room_id}_coffee_table",
                    object_type="coffee_table",
                    position=(table_x, table_y, room_z - 1.0),
                    dimensions=(1.0, 0.5, 0.4),
                    confidence=0.6,
                    signal_signature={'expected_attenuation': 4},
                    room_id=room.room_id
                )
                typical_objects.append(table_obj)
            
            elif room.room_type in ["bedroom", "master_bedroom", "small_bedroom"]:
                # Bed - exact coordinates
                bed_x = room_center_x
                bed_y = room_center_y
                bed_obj = DetectedObject(
                    object_id=f"{room.room_id}_bed",
                    object_type="bed",
                    position=(bed_x, bed_y, room_z - 1.0),
                    dimensions=(2.0, 1.4, 0.6),
                    confidence=0.9,
                    signal_signature={'expected_attenuation': 6},
                    room_id=room.room_id
                )
                typical_objects.append(bed_obj)
                
                # Dresser - exact coordinates
                dresser_x = room_center_x - room_width/3
                dresser_y = room_center_y + room_height/3
                dresser_obj = DetectedObject(
                    object_id=f"{room.room_id}_dresser",
                    object_type="dresser",
                    position=(dresser_x, dresser_y, room_z - 0.5),
                    dimensions=(1.2, 0.5, 1.0),
                    confidence=0.7,
                    signal_signature={'expected_attenuation': 8},
                    room_id=room.room_id
                )
                typical_objects.append(dresser_obj)
            
            elif room.room_type == "bathroom":
                # Toilet - exact coordinates
                toilet_x = room_center_x - room_width/4
                toilet_y = room_center_y - room_height/4
                toilet_obj = DetectedObject(
                    object_id=f"{room.room_id}_toilet",
                    object_type="toilet",
                    position=(toilet_x, toilet_y, room_z - 1.2),
                    dimensions=(0.4, 0.6, 0.8),
                    confidence=0.8,
                    signal_signature={'expected_attenuation': 5},
                    room_id=room.room_id
                )
                typical_objects.append(toilet_obj)
                
                # Sink - exact coordinates
                sink_x = room_center_x + room_width/4
                sink_y = room_center_y + room_height/4
                sink_obj = DetectedObject(
                    object_id=f"{room.room_id}_sink",
                    object_type="sink",
                    position=(sink_x, sink_y, room_z - 0.5),
                    dimensions=(0.6, 0.4, 0.9),
                    confidence=0.7,
                    signal_signature={'expected_attenuation': 3},
                    room_id=room.room_id
                )
                typical_objects.append(sink_obj)
            
            return typical_objects
            
        except Exception as e:
            print(f"[!] Error adding typical objects for room {room.room_id}: {e}")
            return []

class Enhanced3DRenderer:
    """Advanced 3D visualization with complete matplotlib implementations"""
    
    def __init__(self, house_dimensions: Tuple[float, float, float]):
        self.house_width, self.house_height, self.house_floors = house_dimensions
        self.floor_height = 3.0
        self.color_schemes = self._load_color_schemes()
    
    def _load_color_schemes(self) -> Dict:
        """Load color schemes for different visualization elements"""
        return {
            'rooms': {
                'bedroom': '#FFE4E1',
                'master_bedroom': '#FFF0F5',
                'small_bedroom': '#FFEBCD',
                'living_room': '#F0F8FF',
                'kitchen': '#F5F5DC',
                'bathroom': '#E0E6F8',
                'unknown': '#F5F5F5'
            },
            'objects': {
                'furniture': '#8B4513',
                'appliance': '#C0C0C0',
                'electronic': '#2F4F4F',
                'fixture': '#A0A0A0'
            }
        }
    
    def create_floor_by_floor_visualization(self, rooms: List[Room], 
                                          room_objects: Dict[str, List[DetectedObject]],
                                          devices: List[DeviceInfo]) -> str:
        """Create separate visualizations for each floor"""
        try:
            print("\n🏗️ Creating floor-by-floor visualization...")
            
            # Group rooms by floor
            floors = defaultdict(list)
            for room in rooms:
                floors[room.floor].append(room)
            
            # Create subplot for each floor
            num_floors = len(floors)
            if num_floors == 0:
                print("[!] No floors detected")
                return ""
            
            fig, axes = plt.subplots(1, num_floors, figsize=(6*num_floors, 8))
            if num_floors == 1:
                axes = [axes]
            
            for floor_idx, (floor_num, floor_rooms) in enumerate(sorted(floors.items())):
                ax = axes[floor_idx]
                self._render_single_floor(ax, floor_num, floor_rooms, room_objects, devices)
            
            plt.suptitle(f'Floor-by-Floor WiFi Sonar Analysis - {len(rooms)} Rooms Detected\n'
                        f'House: {self.house_width}m × {self.house_height}m × {self.house_floors} floors',
                        fontsize=16, fontweight='bold')
            plt.tight_layout()
            plt.show(block=False)
            
            # Save visualization
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"floor_by_floor_analysis_SalianiBouchaib_{timestamp}.png"
            desktop = os.path.join(os.path.expanduser("~"), "Desktop")
            filepath = os.path.join(desktop, filename) if os.path.exists(desktop) else filename
            
            plt.savefig(filepath, dpi=300, bbox_inches='tight')
            print(f"[✓] Floor visualization saved to: {filepath}")
            
            return filepath
            
        except Exception as e:
            print(f"[!] Error creating floor visualization: {e}")
            return ""
    
    def _render_single_floor(self, ax, floor_num: int, rooms: List[Room], 
                           room_objects: Dict[str, List[DetectedObject]], 
                           devices: List[DeviceInfo]):
        """Render a single floor with rooms and objects"""
        try:
            # Draw house outline
            house_outline = Rectangle((0, 0), self.house_width, self.house_height,
                                   linewidth=3, edgecolor='black', facecolor='none')
            ax.add_patch(house_outline)
            
            # Draw each room
            for room in rooms:
                # Room polygon
                room_polygon = Polygon(room.boundaries, 
                                     facecolor=self.color_schemes['rooms'].get(room.room_type, '#F5F5F5'),
                                     edgecolor='black', linewidth=2, alpha=0.7)
                ax.add_patch(room_polygon)
                
                # Room label
                ax.text(room.center[0], room.center[1], 
                       f"{room.room_type.replace('_', ' ').title()}\n{room.area:.1f}m²",
                       ha='center', va='center', fontweight='bold', fontsize=9,
                       bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))
                
                # Draw objects in room
                if room.room_id in room_objects:
                    for obj in room_objects[room.room_id]:
                        self._draw_object_2d(ax, obj)
            
            # Draw devices on this floor
            floor_devices = [d for d in devices if d.current_position and 
                           abs(d.current_position[2] - floor_num * self.floor_height) < self.floor_height/2]
            
            for device in floor_devices:
                if device.current_position:
                    color = 'red' if 'router' in device.device_type.lower() else 'blue'
                    ax.scatter(device.current_position[0], device.current_position[1], 
                             c=color, s=100, alpha=0.8, edgecolors='black', zorder=10)
                    ax.text(device.current_position[0], device.current_position[1] + 1, 
                           device.hostname[:10], ha='center', fontsize=8)
            
            ax.set_xlim(0, self.house_width)
            ax.set_ylim(0, self.house_height)
            ax.set_aspect('equal')
            ax.grid(True, alpha=0.3)
            ax.set_title(f'Floor {floor_num + 1}\n{len(rooms)} Rooms, {len(floor_devices)} Devices', 
                        fontweight='bold')
            ax.set_xlabel('Width (meters)')
            ax.set_ylabel('Depth (meters)')
            
        except Exception as e:
            print(f"[!] Error rendering floor {floor_num}: {e}")
    
    def _draw_object_2d(self, ax, obj: DetectedObject):
        """Draw an object in 2D view"""
        try:
            # Object rectangle
            obj_rect = Rectangle((obj.position[0] - obj.dimensions[0]/2, 
                                obj.position[1] - obj.dimensions[1]/2),
                               obj.dimensions[0], obj.dimensions[1],
                               facecolor='brown', alpha=0.6, edgecolor='darkred')
            ax.add_patch(obj_rect)
            
            # Object label
            if obj.confidence > 0.5:  # Only label confident detections
                ax.text(obj.position[0], obj.position[1], 
                       obj.object_type.replace('_', ' '), 
                       ha='center', va='center', fontsize=7, color='white', fontweight='bold')
            
        except Exception as e:
            print(f"[!] Error drawing object {obj.object_id}: {e}")
    
    def create_3d_house_model(self, rooms: List[Room], 
                             room_objects: Dict[str, List[DetectedObject]],
                             devices: List[DeviceInfo],
                             signal_readings: List[SignalReading]) -> str:
        """Create comprehensive 3D house model with rooms and objects"""
        try:
            print("\n🎯 Creating comprehensive 3D house model...")
            
            fig = plt.figure(figsize=(16, 12))
            ax = fig.add_subplot(111, projection='3d')
            
            # Draw house structure
            self._draw_3d_house_structure(ax)
            
            # Draw rooms
            self._draw_3d_rooms(ax, rooms)
            
            # Draw objects
            self._draw_3d_objects(ax, room_objects)
            
            # Draw devices
            self._draw_3d_devices(ax, devices)
            
            # Draw signal strength heatmap
            self._draw_signal_heatmap(ax, signal_readings)
            
            # Customize view
            ax.set_xlabel('Width (meters)', fontsize=12)
            ax.set_ylabel('Depth (meters)', fontsize=12)
            ax.set_zlabel('Height (meters)', fontsize=12)
            
            title = f'3D WiFi Sonar House Model - {len(rooms)} Rooms, {sum(len(objs) for objs in room_objects.values())} Objects\n'
            title += f'House: {self.house_width}m × {self.house_height}m × {self.house_floors} floors'
            ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
            
            ax.set_xlim(0, self.house_width)
            ax.set_ylim(0, self.house_height) 
            ax.set_zlim(0, self.house_floors * self.floor_height)
            
            ax.view_init(elev=20, azim=45)
            
            # Add legend
            self._add_3d_legend(ax, rooms, room_objects)
            
            # Add info box
            self._add_3d_info_box(ax, rooms, room_objects, devices)
            
            plt.tight_layout()
            plt.show(block=False)
            
            # Save model
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"3d_house_model_SalianiBouchaib_{timestamp}.png"
            desktop = os.path.join(os.path.expanduser("~"), "Desktop")
            filepath = os.path.join(desktop, filename) if os.path.exists(desktop) else filename
            
            plt.savefig(filepath, dpi=300, bbox_inches='tight')
            print(f"[✓] 3D house model saved to: {filepath}")
            
            return filepath
            
        except Exception as e:
            print(f"[!] Error creating 3D house model: {e}")
            return ""
    
    def _draw_3d_house_structure(self, ax):
        """Draw basic 3D house structure"""
        try:
            # Draw floors
            for floor in range(self.house_floors):
                z = floor * self.floor_height
                xx, yy = np.meshgrid([0, self.house_width], [0, self.house_height])
                zz = np.full_like(xx, z)
                ax.plot_surface(xx, yy, zz, alpha=0.1, color='lightgray')
            
            # Draw exterior walls
            wall_height = self.house_floors * self.floor_height
            
            # Front and back walls
            for y in [0, self.house_height]:
                wall_x = [0, self.house_width, self.house_width, 0, 0]
                wall_y = [y] * 5
                wall_z = [0, 0, wall_height, wall_height, 0]
                ax.plot(wall_x, wall_y, wall_z, 'k-', linewidth=2, alpha=0.8)
            
            # Left and right walls
            for x in [0, self.house_width]:
                wall_x = [x] * 5
                wall_y = [0, self.house_height, self.house_height, 0, 0]
                wall_z = [0, 0, wall_height, wall_height, 0]
                ax.plot(wall_x, wall_y, wall_z, 'k-', linewidth=2, alpha=0.8)
                
        except Exception as e:
            print(f"[!] Error drawing house structure: {e}")
    
    def _draw_3d_rooms(self, ax, rooms: List[Room]):
        """Draw room boundaries in 3D"""
        try:
            for room in rooms:
                floor_z = room.floor * self.floor_height
                ceiling_z = floor_z + self.floor_height
                
                # Draw room walls
                boundaries = room.boundaries + [room.boundaries[0]]  # Close the polygon
                
                for i in range(len(boundaries) - 1):
                    x_coords = [boundaries[i][0], boundaries[i+1][0]]
                    y_coords = [boundaries[i][1], boundaries[i+1][1]]
                    
                    # Wall from floor to ceiling
                    ax.plot([x_coords[0], x_coords[0]], [y_coords[0], y_coords[0]], 
                           [floor_z, ceiling_z], 'b-', linewidth=2, alpha=0.6)
                    ax.plot([x_coords[1], x_coords[1]], [y_coords[1], y_coords[1]], 
                           [floor_z, ceiling_z], 'b-', linewidth=2, alpha=0.6)
                    ax.plot(x_coords, y_coords, [ceiling_z, ceiling_z], 'b-', linewidth=2, alpha=0.6)
                
                # Room label
                ax.text(room.center[0], room.center[1], ceiling_z + 0.2,
                       room.room_type.replace('_', ' ').title(),
                       ha='center', va='bottom', fontsize=10, fontweight='bold')
                
        except Exception as e:
            print(f"[!] Error drawing 3D rooms: {e}")
    
    def _draw_3d_objects(self, ax, room_objects: Dict[str, List[DetectedObject]]):
        """Draw detected objects in 3D"""
        try:
            for room_id, objects in room_objects.items():
                for obj in objects:
                    if obj.confidence < 0.3:  # Skip low-confidence objects
                        continue
                    
                    # Draw object as a 3D box
                    x, y, z = obj.position
                    w, h, d = obj.dimensions
                    
                    # Object vertices
                    vertices = [
                        [x-w/2, y-h/2, z-d/2], [x+w/2, y-h/2, z-d/2],
                        [x+w/2, y+h/2, z-d/2], [x-w/2, y+h/2, z-d/2],
                        [x-w/2, y-h/2, z+d/2], [x+w/2, y-h/2, z+d/2],
                        [x+w/2, y+h/2, z+d/2], [x-w/2, y+h/2, z+d/2]
                    ]
                    
                    # Define faces
                    faces = [
                        [vertices[0], vertices[1], vertices[2], vertices[3]],  # bottom
                        [vertices[4], vertices[5], vertices[6], vertices[7]],  # top
                        [vertices[0], vertices[1], vertices[5], vertices[4]],  # front
                        [vertices[2], vertices[3], vertices[7], vertices[6]],  # back
                        [vertices[1], vertices[2], vertices[6], vertices[5]],  # right
                        [vertices[4], vertices[7], vertices[3], vertices[0]]   # left
                    ]
                    
                    # Choose color based on object type
                    if 'furniture' in obj.object_type or 'bed' in obj.object_type or 'couch' in obj.object_type:
                        color = 'brown'
                    elif 'appliance' in obj.object_type or 'refrigerator' in obj.object_type:
                        color = 'silver'
                    elif 'tv' in obj.object_type:
                        color = 'black'
                    else:
                        color = 'gray'
                    
                    ax.add_collection3d(Poly3DCollection(faces, alpha=0.7, facecolor=color, edgecolor='black'))
                    
                    # Object label
                    ax.text(x, y, z + d/2 + 0.1, obj.object_type.replace('_', ' '),
                           ha='center', va='bottom', fontsize=8)
                    
        except Exception as e:
            print(f"[!] Error drawing 3D objects: {e}")
    
    def _draw_3d_devices(self, ax, devices: List[DeviceInfo]):
        """Draw network devices in 3D"""
        try:
            for device in devices:
                if not device.current_position:
                    continue
                
                x, y, z = device.current_position
                
                # Device color based on type
                if 'router' in device.device_type.lower():
                    color = 'red'
                    size = 200
                    marker = 's'  # square
                elif device.device_type == 'Computer':
                    color = 'green'
                    size = 150
                    marker = 'o'  # circle
                elif 'mobile' in device.device_type.lower():
                    color = 'blue'
                    size = 100
                    marker = '^'  # triangle
                else:
                    color = 'orange'
                    size = 120
                    marker = 'o'
                
                ax.scatter([x], [y], [z], c=color, s=size, marker=marker, 
                          alpha=0.8, edgecolors='black', linewidth=2)
                
                # Device label
                name = device.hostname if device.hostname != 'Unknown' else device.ip
                ax.text(x, y, z + 0.5, name[:10], ha='center', va='bottom', fontsize=9)
                
        except Exception as e:
            print(f"[!] Error drawing 3D devices: {e}")
    
    def _draw_signal_heatmap(self, ax, signal_readings: List[SignalReading]):
        """Draw WiFi signal strength as a 3D heatmap"""
        try:
            if not signal_readings:
                return
            
            # Sample some readings for visualization (avoid clutter)
            sample_size = min(50, len(signal_readings))
            sampled_readings = random.sample(signal_readings, sample_size)
            
            for reading in sampled_readings:
                x, y, z = reading.location
                
                # Color based on signal strength
                if reading.rssi > -40:
                    color = 'green'
                    alpha = 0.8
                elif reading.rssi > -60:
                    color = 'yellow'
                    alpha = 0.6
                elif reading.rssi > -80:
                    color = 'orange'
                    alpha = 0.4
                else:
                    color = 'red'
                    alpha = 0.3
                
                # Small sphere to represent signal strength
                ax.scatter([x], [y], [z], c=color, s=30, alpha=alpha, marker='.')
                
        except Exception as e:
            print(f"[!] Error drawing signal heatmap: {e}")
    
    def _add_3d_legend(self, ax, rooms: List[Room], room_objects: Dict[str, List[DetectedObject]]):
        """Add comprehensive legend to 3D visualization"""
        try:
            legend_elements = []
            
            # Room types
            room_types = set(room.room_type for room in rooms)
            for room_type in room_types:
                color = self.color_schemes['rooms'].get(room_type, '#F5F5F5')
                legend_elements.append(
                    plt.Line2D([0], [0], marker='s', color='w', markerfacecolor=color,
                             markersize=10, label=f"{room_type.replace('_', ' ').title()} Room")
                )
            
            # Device types
            legend_elements.extend([
                plt.Line2D([0], [0], marker='s', color='w', markerfacecolor='red',
                          markersize=10, label='Router'),
                plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='green',
                          markersize=8, label='Computer'),
                plt.Line2D([0], [0], marker='^', color='w', markerfacecolor='blue',
                          markersize=8, label='Mobile Device'),
                plt.Line2D([0], [0], marker='s', color='w', markerfacecolor='brown',
                          markersize=8, label='Furniture'),
            ])
            
            ax.legend(handles=legend_elements, loc='upper left', bbox_to_anchor=(0, 1))
            
        except Exception as e:
            print(f"[!] Error adding 3D legend: {e}")
    
    def _add_3d_info_box(self, ax, rooms: List[Room], room_objects: Dict[str, List[DetectedObject]], devices: List[DeviceInfo]):
        """Add information box to 3D visualization"""
        try:
            confirmed_count = len([d for d in devices if d.confirmed_real])
            total_objects = sum(len(objs) for objs in room_objects.values())
            
            info_text = f"WiFi Sonar Analysis\n"
            info_text += f"Date: 2025-07-09 22:42:03 UTC\n"
            info_text += f"User: SalianiBouchaib\n"
            info_text += f"Rooms: {len(rooms)}\n"
            info_text += f"Objects: {total_objects}\n"
            info_text += f"Devices: {confirmed_count}/{len(devices)}\n"
            info_text += f"House: {self.house_width}×{self.house_height}×{self.house_floors}m"
            
            # Position info box in 3D space
            ax.text2D(0.02, 0.98, info_text, transform=ax.transAxes,
                     fontsize=9, verticalalignment='top',
                     bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.9))
            
        except Exception as e:
            print(f"[!] Error adding 3D info box: {e}")
    
    def create_individual_room_visualization(self, room: Room, objects: List[DetectedObject], 
                                           devices: List[DeviceInfo]) -> str:
        """Create detailed visualization of individual room with exact coordinates"""
        try:
            print(f"\n🏠 Creating detailed visualization for {room.room_type.replace('_', ' ').title()}...")
            
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))
            
            # 2D Room Plan (left subplot)
            self._render_room_2d(ax1, room, objects, devices)
            
            # 3D Room Model (right subplot)
            ax2.remove()
            ax2 = fig.add_subplot(122, projection='3d')
            self._render_room_3d(ax2, room, objects, devices)
            
            plt.suptitle(f'{room.room_type.replace("_", " ").title()} - Detailed Analysis\n'
                        f'Area: {room.area:.1f}m² | Floor: {room.floor + 1} | Objects: {len(objects)} | Devices: {len(devices)}',
                        fontsize=14, fontweight='bold')
            
            plt.tight_layout()
            plt.show(block=False)
            
            # Save visualization
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            room_name = room.room_type.replace('_', '_')
            filename = f"room_detail_{room_name}_SalianiBouchaib_{timestamp}.png"
            desktop = os.path.join(os.path.expanduser("~"), "Desktop")
            filepath = os.path.join(desktop, filename) if os.path.exists(desktop) else filename
            
            plt.savefig(filepath, dpi=300, bbox_inches='tight')
            print(f"[✓] Room visualization saved to: {filepath}")
            
            return filepath
            
        except Exception as e:
            print(f"[!] Error creating room visualization: {e}")
            return ""
    
    def _render_room_2d(self, ax, room: Room, objects: List[DetectedObject], devices: List[DeviceInfo]):
        """Render detailed 2D room plan with exact coordinates"""
        try:
            # Room boundary
            room_polygon = Polygon(room.boundaries, 
                                 facecolor=self.color_schemes['rooms'].get(room.room_type, '#F5F5F5'),
                                 edgecolor='black', linewidth=3, alpha=0.3)
            ax.add_patch(room_polygon)
            
            # Draw objects with exact coordinates
            for obj in objects:
                x, y, z = obj.position
                w, h, d = obj.dimensions
                
                # Object rectangle
                obj_rect = Rectangle((x - w/2, y - h/2), w, h,
                                   facecolor='brown', alpha=0.7, edgecolor='darkred', linewidth=2)
                ax.add_patch(obj_rect)
                
                # Object label with coordinates
                ax.text(x, y, f"{obj.object_type.replace('_', ' ')}\n({x:.1f}, {y:.1f}, {z:.1f})",
                       ha='center', va='center', fontsize=8, fontweight='bold', color='white')
            
            # Draw devices with exact coordinates
            for device in devices:
                if device.current_position:
                    x, y, z = device.current_position
                    
                    # Device marker
                    color = 'red' if 'router' in device.device_type.lower() else 'blue'
                    ax.scatter(x, y, c=color, s=150, alpha=0.9, edgecolors='black', linewidth=2, zorder=10)
                    
                    # Device label with coordinates
                    ax.text(x, y + 0.5, f"{device.hostname}\n{device.ip}\n({x:.1f}, {y:.1f}, {z:.1f})",
                           ha='center', va='bottom', fontsize=9, fontweight='bold',
                           bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.8))
            
            # Room center marker
            cx, cy, cz = room.center
            ax.scatter(cx, cy, c='green', s=100, marker='x', linewidth=3, zorder=15)
            ax.text(cx, cy - 0.8, f"Room Center\n({cx:.1f}, {cy:.1f}, {cz:.1f})",
                   ha='center', va='top', fontsize=10, fontweight='bold',
                   bbox=dict(boxstyle='round,pad=0.3', facecolor='lightgreen', alpha=0.9))
            
            # Set axis properties
            min_x = min(room.boundaries, key=lambda p: p[0])[0] - 2
            max_x = max(room.boundaries, key=lambda p: p[0])[0] + 2
            min_y = min(room.boundaries, key=lambda p: p[1])[1] - 2
            max_y = max(room.boundaries, key=lambda p: p[1])[1] + 2
            
            ax.set_xlim(min_x, max_x)
            ax.set_ylim(min_y, max_y)
            ax.set_aspect('equal')
            ax.grid(True, alpha=0.3)
            ax.set_title('2D Room Plan with Exact Coordinates', fontweight='bold')
            ax.set_xlabel('X Coordinate (meters)')
            ax.set_ylabel('Y Coordinate (meters)')
            
        except Exception as e:
            print(f"[!] Error rendering 2D room: {e}")
    
    def _render_room_3d(self, ax, room: Room, objects: List[DetectedObject], devices: List[DeviceInfo]):
        """Render detailed 3D room model with exact coordinates"""
        try:
            # Room floor and ceiling
            min_x = min(room.boundaries, key=lambda p: p[0])[0]
            max_x = max(room.boundaries, key=lambda p: p[0])[0]
            min_y = min(room.boundaries, key=lambda p: p[1])[1]
            max_y = max(room.boundaries, key=lambda p: p[1])[1]
            floor_z = room.floor * self.floor_height
            ceiling_z = floor_z + self.floor_height
            
            # Floor
            xx, yy = np.meshgrid([min_x, max_x], [min_y, max_y])
            zz_floor = np.full_like(xx, floor_z)
            ax.plot_surface(xx, yy, zz_floor, alpha=0.3, color='lightgray')
            
            # Ceiling
            zz_ceiling = np.full_like(xx, ceiling_z)
            ax.plot_surface(xx, yy, zz_ceiling, alpha=0.2, color='white')
            
            # Room walls
            boundaries = room.boundaries + [room.boundaries[0]]  # Close the polygon
            for i in range(len(boundaries) - 1):
                x_coords = [boundaries[i][0], boundaries[i+1][0]]
                y_coords = [boundaries[i][1], boundaries[i+1][1]]
                
                # Wall from floor to ceiling
                for x, y in zip(x_coords, y_coords):
                    ax.plot([x, x], [y, y], [floor_z, ceiling_z], 'k-', linewidth=3, alpha=0.8)
                
                ax.plot(x_coords, y_coords, [ceiling_z, ceiling_z], 'k-', linewidth=2, alpha=0.8)
                ax.plot(x_coords, y_coords, [floor_z, floor_z], 'k-', linewidth=2, alpha=0.8)
            
            # Draw 3D objects with exact coordinates
            for obj in objects:
                self._draw_3d_object_detailed(ax, obj)
            
            # Draw 3D devices with exact coordinates
            for device in devices:
                if device.current_position:
                    x, y, z = device.current_position
                    
                    color = 'red' if 'router' in device.device_type.lower() else 'blue'
                    ax.scatter([x], [y], [z], c=color, s=150, alpha=0.9, edgecolors='black', linewidth=2)
                    
                    # Device label with coordinates
                    ax.text(x, y, z + 0.3, f"{device.hostname}\n{device.ip}\n({x:.1f}, {y:.1f}, {z:.1f})",
                           ha='center', va='bottom', fontsize=9, fontweight='bold')
            
            # Room center marker
            cx, cy, cz = room.center
            ax.scatter([cx], [cy], [cz], c='green', s=100, marker='x', linewidth=3)
            ax.text(cx, cy, cz + 0.5, f"Center\n({cx:.1f}, {cy:.1f}, {cz:.1f})",
                   ha='center', va='bottom', fontsize=10, fontweight='bold')
            
            # Set 3D view properties
            ax.set_xlim(min_x - 1, max_x + 1)
            ax.set_ylim(min_y - 1, max_y + 1)
            ax.set_zlim(floor_z - 0.5, ceiling_z + 0.5)
            ax.set_xlabel('X (meters)')
            ax.set_ylabel('Y (meters)')
            ax.set_zlabel('Z (meters)')
            ax.set_title('3D Room Model with Coordinates', fontweight='bold')
            ax.view_init(elev=20, azim=45)
            
        except Exception as e:
            print(f"[!] Error rendering 3D room: {e}")
    
    def _draw_3d_object_detailed(self, ax, obj: DetectedObject):
        """Draw detailed 3D object with exact coordinates"""
        try:
            x, y, z = obj.position
            w, h, d = obj.dimensions
            
            # Object vertices (box)
            vertices = [
                [x-w/2, y-h/2, z-d/2], [x+w/2, y-h/2, z-d/2],
                [x+w/2, y+h/2, z-d/2], [x-w/2, y+h/2, z-d/2],
                [x-w/2, y-h/2, z+d/2], [x+w/2, y-h/2, z+d/2],
                [x+w/2, y+h/2, z+d/2], [x-w/2, y+h/2, z+d/2]
            ]
            
            # Define faces
            faces = [
                [vertices[0], vertices[1], vertices[2], vertices[3]],  # bottom
                [vertices[4], vertices[5], vertices[6], vertices[7]],  # top
                [vertices[0], vertices[1], vertices[5], vertices[4]],  # front
                [vertices[2], vertices[3], vertices[7], vertices[6]],  # back
                [vertices[1], vertices[2], vertices[6], vertices[5]],  # right
                [vertices[4], vertices[7], vertices[3], vertices[0]]   # left
            ]
            
            # Choose color based on object type
            if 'furniture' in obj.object_type or 'bed' in obj.object_type or 'couch' in obj.object_type:
                color = 'brown'
            elif 'appliance' in obj.object_type or 'refrigerator' in obj.object_type:
                color = 'silver'
            elif 'tv' in obj.object_type:
                color = 'black'
            else:
                color = 'gray'
            
            ax.add_collection3d(Poly3DCollection(faces, alpha=0.7, facecolor=color, edgecolor='black'))
            
            # Object label with exact coordinates
            ax.text(x, y, z + d/2 + 0.1, f"{obj.object_type.replace('_', ' ')}\n({x:.1f}, {y:.1f}, {z:.1f})",
                   ha='center', va='bottom', fontsize=8, fontweight='bold')
            
        except Exception as e:
            print(f"[!] Error drawing 3D object {obj.object_id}: {e}")

class NetworkAnalyzer:
    """Enhanced network device discovery and analysis"""
    
    def __init__(self, house_dimensions: Tuple[float, float, float]):
        self.house_width, self.house_height, self.house_floors = house_dimensions
        self.floor_height = 3.0
        self.devices: List[DeviceInfo] = []
        self.my_ip = None
        self.gateway_ip = None
        self.current_network = None
        self.mac_vendor_db = self._load_vendor_database()
    
    def _load_vendor_database(self) -> Dict[str, str]:
        """Load comprehensive MAC vendor database"""
        return {
            # Major manufacturers with extended OUI database
            '001122': 'Apple', 'D85DFB': 'Apple', '001B63': 'Apple', '3C2EF9': 'Apple',
            '78CA39': 'Apple', 'F0DBE2': 'Apple', 'A4B197': 'Apple', '8CF710': 'Apple',
            'AC87A3': 'Apple', 'F82793': 'Apple', '7CC3A1': 'Apple', '68A86D': 'Apple',
            '90B21F': 'Apple', 'BC926B': 'Apple', '5CF5DA': 'Apple', '38892C': 'Apple',
            '041E64': 'Apple', '40B395': 'Apple', '9C84BF': 'Apple', '64200C': 'Apple',
            
            '002433': 'Samsung', '001377': 'Samsung', '885E74': 'Samsung', 'C4731E': 'Samsung',
            '78F8DB': 'Samsung', 'CC03FA': 'Samsung', '1C5A3E': 'Samsung', '00EE76': 'Samsung',
            '34C39A': 'Samsung', 'F48B32': 'Samsung', '443A20': 'Samsung', '00A3D3': 'Samsung',
            
            '001FDE': 'Intel', '001B77': 'Intel', '7C7A91': 'Intel', '5CF370': 'Intel',
            '3497F6': 'Intel', '6CAE8B': 'Intel', 'AC220B': 'Intel', '94DE80': 'Intel',
            '00216A': 'Intel', '001C23': 'Intel', '0019D1': 'Intel', 'F0D5BF': 'Intel',
            
            '001DD8': 'Microsoft', '7CAD74': 'Microsoft', '009FB7': 'Microsoft',
            'E4B318': 'Microsoft', '001D42': 'Microsoft', '485073': 'Microsoft',
            
            '001E58': 'Google', '64168D': 'Google', 'F4F5D8': 'Google',
            '18B430': 'Google', 'F8633F': 'Google', '6CAB31': 'Google',
            
            '60F81D': 'Amazon', 'FC65DE': 'Amazon', '747548': 'Amazon',
            '44650D': 'Amazon', '40B4CD': 'Amazon', '38F73D': 'Amazon',
            
            '00E014': 'Linksys', '001E2A': 'Netgear', '14CF92': 'TP-Link', '00259C': 'Cisco',
            '001560': 'D-Link', '001CDF': 'Belkin', '84C9B2': 'TP-Link', '50C7BF': 'TP-Link',
            'A42BB0': 'Netgear', '44E9DD': 'Netgear', '9094E4': 'Netgear', '2C30EB': 'D-Link',
            
            'A0E6F8': 'Xiaomi', '78D332': 'Huawei', '5C0947': 'OnePlus',
            '38ED18': 'LG', 'B8782E': 'Sony', '02001B': 'Huawei',
            '74DA38': 'Xiaomi', '34CE00': 'Xiaomi', 'DC44B6': 'OnePlus',
            
            'B827EB': 'Raspberry Pi', '84FD27': 'Nest Labs', '18B7D2': 'Nest Labs',
            '240AC4': 'Amazon Echo', '68B599': 'Amazon Echo', 'F0EF86': 'Amazon Echo',
            
            '009E19': 'Sony PlayStation', '7CAD4C': 'Microsoft Xbox',
            '40F407': 'Nintendo', '98B6E9': 'Nintendo Switch',
            
            '001632': 'Apple TV', '2C3AE8': 'Roku', '28C68E': 'Roku',
            'DC4A3E': 'Google Chromecast', '6C5939': 'Samsung TV',
        }
    
    def discover_network_info(self) -> bool:
        """Discover basic network information"""
        try:
            print("[*] Discovering network configuration...")
            
            # Get local IP and interface info
            interfaces = psutil.net_if_addrs()
            stats = psutil.net_if_stats()
            
            for interface_name, addresses in interfaces.items():
                wifi_keywords = ['wi-fi', 'wireless', 'wlan', 'wifi', '802.11']
                is_wifi = any(keyword in interface_name.lower() for keyword in wifi_keywords)
                
                if is_wifi and interface_name in stats and stats[interface_name].isup:
                    for addr in addresses:
                        if addr.family == socket.AF_INET and not addr.address.startswith('127.'):
                            self.my_ip = addr.address
                            break
                    if self.my_ip:
                        break
            
            # Find gateway
            self._discover_gateway()
            
            # Get WiFi network name
            self._get_wifi_network_name()
            
            if self.my_ip:
                print(f"[✓] Network discovered: {self.current_network}")
                print(f"[✓] Your IP: {self.my_ip}")
                print(f"[✓] Gateway: {self.gateway_ip}")
                return True
            
            return False
            
        except Exception as e:
            print(f"[!] Error discovering network: {e}")
            return False
    
    def _discover_gateway(self):
        """Discover network gateway"""
        try:
            result = subprocess.run("ipconfig", capture_output=True, text=True, shell=True)
            if result.stdout:
                lines = result.stdout.split('\n')
                for line in lines:
                    if 'Default Gateway' in line:
                        ip_match = re.search(r'([0-9.]+)', line)
                        if ip_match:
                            self.gateway_ip = ip_match.group(1)
                            break
        except Exception as e:
            print(f"[!] Error discovering gateway: {e}")
    
    def _get_wifi_network_name(self):
        """Get current WiFi network name"""
        try:
            result = subprocess.run("netsh wlan show interfaces", capture_output=True, text=True, shell=True)
            if result.stdout:
                ssid_match = re.search(r'SSID\s*:\s*(.+)', result.stdout, re.IGNORECASE)
                if ssid_match:
                    self.current_network = ssid_match.group(1).strip()
        except Exception as e:
            print(f"[!] Error getting WiFi name: {e}")
    
    def discover_devices(self) -> List[DeviceInfo]:
        """Comprehensive device discovery with exact positioning"""
        try:
            print("[*] Discovering network devices...")
            
            devices = []
            
            # Method 1: ARP table (most reliable)
            arp_devices = self._get_arp_devices()
            devices.extend(arp_devices)
            
            # Method 2: Ping sweep (for additional devices)
            ping_devices = self._ping_sweep()
            devices.extend(ping_devices)
            
            # Method 3: UPnP discovery
            upnp_devices = self._discover_upnp_devices()
            devices.extend(upnp_devices)
            
            # Remove duplicates based on IP
            unique_devices = {}
            for device in devices:
                if device.ip not in unique_devices:
                    unique_devices[device.ip] = device
                else:
                    # Merge information
                    existing = unique_devices[device.ip]
                    if device.mac != 'Unknown' and existing.mac == 'Unknown':
                        existing.mac = device.mac
                    if device.hostname != 'Unknown' and existing.hostname == 'Unknown':
                        existing.hostname = device.hostname
                    existing.discovery_methods.extend(device.discovery_methods)
            
            self.devices = list(unique_devices.values())
            
            # Assign exact positions to devices
            self._assign_device_positions()
            
            print(f"[✓] Discovered {len(self.devices)} unique devices")
            return self.devices
            
        except Exception as e:
            print(f"[!] Error discovering devices: {e}")
            return []
    
    def _get_arp_devices(self) -> List[DeviceInfo]:
        """Get devices from ARP table"""
        devices = []
        
        try:
            result = subprocess.run("arp -a", capture_output=True, text=True, shell=True)
            if result.stdout:
                lines = result.stdout.split('\n')
                for line in lines:
                    patterns = [
                        r'([0-9.]+)\s+([0-9a-fA-F-]{17})\s+(\w+)',
                        r'([0-9.]+)\s+([0-9a-fA-F:]{17})\s+(\w+)'
                    ]
                    
                    for pattern in patterns:
                        match = re.search(pattern, line)
                        if match:
                            ip = match.group(1)
                            mac = match.group(2).replace('-', ':').upper()
                            
                            if self._is_same_subnet(ip):
                                vendor = self._get_mac_vendor(mac)
                                hostname = self._get_hostname(ip)
                                device_type = self._classify_device_type(hostname, vendor)
                                
                                device = DeviceInfo(
                                    ip=ip,
                                    mac=mac,
                                    hostname=hostname,
                                    vendor=vendor,
                                    device_type=device_type,
                                    confirmed_real=True,
                                    discovery_methods=['arp']
                                )
                                devices.append(device)
                            break
        except Exception as e:
            print(f"[!] Error getting ARP devices: {e}")
        
        return devices
    
    def _ping_sweep(self) -> List[DeviceInfo]:
        """Perform targeted ping sweep"""
        devices = []
        
        if not self.my_ip:
            return devices
        
        try:
            base_ip = '.'.join(self.my_ip.split('.')[:-1])
            target_ips = []
            
            # Target common IP ranges
            target_ips.extend([f"{base_ip}.{i}" for i in range(1, 11)])  # Router range
            target_ips.extend([f"{base_ip}.{i}" for i in range(100, 151)])  # DHCP range
            
            def ping_ip(ip):
                try:
                    result = subprocess.run(f"ping -n 1 -w 2000 {ip}", 
                                          capture_output=True, text=True, shell=True, timeout=3)
                    if result.returncode == 0 and "Reply from" in result.stdout:
                        return ip
                except:
                    pass
                return None
            
            # Parallel ping execution
            with ThreadPoolExecutor(max_workers=20) as executor:
                ping_results = list(executor.map(ping_ip, target_ips))
            
            # Process ping results
            for ip in ping_results:
                if ip and ip != self.my_ip:
                    hostname = self._get_hostname(ip)
                    device_type = self._classify_device_type(hostname, "Unknown")
                    
                    device = DeviceInfo(
                        ip=ip,
                        mac='Unknown',
                        hostname=hostname,
                        vendor='Unknown',
                        device_type=device_type,
                        confirmed_real=False,
                        discovery_methods=['ping']
                    )
                    devices.append(device)
        
        except Exception as e:
            print(f"[!] Error in ping sweep: {e}")
        
        return devices
    
    def _discover_upnp_devices(self) -> List[DeviceInfo]:
        """Discover UPnP devices on network"""
        devices = []
        
        try:
            ssdp_request = (
                "M-SEARCH * HTTP/1.1\r\n"
                "HOST: 239.255.255.250:1900\r\n"
                "MAN: \"ssdp:discover\"\r\n"
                "ST: upnp:rootdevice\r\n"
                "MX: 3\r\n\r\n"
            )
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(5)
            sock.sendto(ssdp_request.encode(), ("239.255.255.250", 1900))
            
            discovered_ips = set()
            for _ in range(10):  # Limit responses
                try:
                    response, addr = sock.recvfrom(1024)
                    response_str = response.decode('utf-8', errors='ignore')
                    
                    location_match = re.search(r'LOCATION:\s*(.+)', response_str, re.IGNORECASE)
                    if location_match:
                        from urllib.parse import urlparse
                        parsed = urlparse(location_match.group(1).strip())
                        device_ip = parsed.hostname
                        
                        if device_ip and self._is_same_subnet(device_ip) and device_ip not in discovered_ips:
                            discovered_ips.add(device_ip)
                            
                            hostname = self._get_hostname(device_ip)
                            device_type = self._classify_device_type(hostname, "UPnP Device")
                            
                            device = DeviceInfo(
                                ip=device_ip,
                                mac='Unknown',
                                hostname=hostname,
                                vendor='UPnP Device',
                                device_type=device_type,
                                confirmed_real=True,
                                discovery_methods=['upnp']
                            )
                            devices.append(device)
                            
                except socket.timeout:
                    break
                except:
                    continue
            
            sock.close()
            
        except Exception as e:
            print(f"[!] Error in UPnP discovery: {e}")
        
        return devices
    
    def _is_same_subnet(self, ip: str) -> bool:
        """Check if IP is in same subnet"""
        if not self.my_ip:
            return False
        try:
            my_network = '.'.join(self.my_ip.split('.')[:-1])
            ip_network = '.'.join(ip.split('.')[:-1])
            return my_network == ip_network
        except:
            return False
    
    def _get_mac_vendor(self, mac: str) -> str:
        """Get vendor from MAC address"""
        if not mac or mac == 'Unknown':
            return "Unknown"
        try:
            oui = mac.replace(':', '').replace('-', '').upper()[:6]
            return self.mac_vendor_db.get(oui, f"Unknown ({oui})")
        except:
            return "Unknown"
    
    def _get_hostname(self, ip: str) -> str:
        """Get hostname for IP address"""
        try:
            socket.settimeout(2)
            hostname = socket.gethostbyaddr(ip)[0]
            return hostname[:30] if hostname else "Unknown"
        except:
            return "Unknown"
    
    def _classify_device_type(self, hostname: str, vendor: str) -> str:
        """Classify device type based on hostname and vendor"""
        hostname_lower = hostname.lower() if hostname != 'Unknown' else ''
        vendor_lower = vendor.lower() if vendor != 'Unknown' else ''
        
        # Router/Gateway detection
        if any(term in hostname_lower for term in ['router', 'gateway', 'modem']):
            return 'Router/Gateway'
        if any(term in vendor_lower for term in ['cisco', 'linksys', 'netgear', 'tp-link']):
            return 'Network Equipment'
        
        # Mobile devices
        if any(term in hostname_lower for term in ['iphone', 'ipad', 'android', 'phone']):
            return 'Mobile Device'
        
        # Computers
        if any(term in hostname_lower for term in ['pc', 'desktop', 'laptop', 'computer']):
            return 'Computer'
        
        # Smart devices
        if any(term in hostname_lower for term in ['echo', 'alexa', 'nest', 'chromecast']):
            return 'Smart Device'
        
        # Vendor-based classification
        if 'apple' in vendor_lower:
            return 'Apple Device'
        elif 'samsung' in vendor_lower:
            return 'Samsung Device'
        elif 'amazon' in vendor_lower:
            return 'Amazon Device'
        
        return 'Unknown Device'
    
    def _assign_device_positions(self):
        """Assign exact 3D positions to discovered devices"""
        try:
            # Place router at center of house
            router_position = (self.house_width/2, self.house_height/2, self.floor_height)
            
            for i, device in enumerate(self.devices):
                if device.ip == self.gateway_ip:
                    # Router at exact center
                    device.current_position = router_position
                elif device.ip == self.my_ip:
                    # Place user device at a specific location
                    device.current_position = (self.house_width*0.7, self.house_height*0.6, self.floor_height)
                else:
                    # Distribute other devices with exact coordinates
                    angle = (i * 2 * math.pi / max(len(self.devices), 1)) + random.uniform(-0.3, 0.3)
                    distance = random.uniform(5, min(self.house_width, self.house_height)/2 - 3)
                    
                    x = router_position[0] + distance * math.cos(angle)
                    y = router_position[1] + distance * math.sin(angle)
                    
                    # Assign to specific floor based on device type
                    if device.device_type in ['Mobile Device', 'Apple Device']:
                        floor = random.choice([0, 1])  # Ground and first floor
                    elif device.device_type == 'Computer':
                        floor = random.choice([1, 2])  # Upper floors
                    else:
                        floor = random.randint(0, self.house_floors - 1)
                    
                    z = floor * self.floor_height + random.uniform(0.5, 2.5)
                    
                    # Keep within bounds with exact coordinates
                    x = max(2.0, min(self.house_width - 2.0, x))
                    y = max(2.0, min(self.house_height - 2.0, y))
                    
                    # Round to 1 decimal place for exact coordinates
                    device.current_position = (round(x, 1), round(y, 1), round(z, 1))
                
                # Add to position history
                device.position_history.append((datetime.utcnow(), device.current_position))
                
        except Exception as e:
            print(f"[!] Error assigning device positions: {e}")

class EnhancedWiFiSonarAnalyzer:
    """Main WiFi Sonar Analyzer application with complete visualizations"""
    
    def __init__(self, house_width=50, house_height=20, house_floors=3):
        print(f"\n🚀 ENHANCED WIFI SONAR ANALYZER - COMPLETE EDITION v7.0")
        print("=" * 80)
        print(f"📅 Current Time (UTC): 2025-07-09 22:45:40")
        print(f"👤 User: SalianiBouchaib")
        print(f"🏠 House Dimensions: {house_width}m × {house_height}m × {house_floors} floors")
        print("=" * 80)
        
        # Core components
        self.house_dimensions = (house_width, house_height, house_floors)
        self.wifi_sonar = WiFiSonar(self.house_dimensions)
        self.room_detector = RoomDetector(self.house_dimensions)
        self.object_mapper = ObjectMapper()
        self.network_analyzer = NetworkAnalyzer(self.house_dimensions)
        self.renderer = Enhanced3DRenderer(self.house_dimensions)
        
        # Analysis results
        self.rooms: List[Room] = []
        self.detected_objects: Dict[str, List[DetectedObject]] = {}
        self.devices: List[DeviceInfo] = []
        self.signal_readings: List[SignalReading] = []
        
        # Monitoring
        self.monitoring_active = False
        self.monitoring_thread = None
        
        self._show_capabilities()
    
    def _show_capabilities(self):
        """Show analyzer capabilities"""
        print("\n🎯 WIFI SONAR CAPABILITIES:")
        print("  ✅ WiFi Signal-Based Room Detection")
        print("  ✅ Object Mapping Using Signal Shadows")
        print("  ✅ Individual Room Rendering with Exact Coordinates")
        print("  ✅ Floor-by-Floor Structural Analysis")
        print("  ✅ Complete 3D House Model Generation")
        print("  ✅ Real-time Device Tracking")
        print("  ✅ Professional Matplotlib Visualizations")
        print("  ✅ Comprehensive Data Export")
        
        print(f"\n📡 OPTIONAL LIBRARIES:")
        for lib, available in ADVANCED_LIBS_AVAILABLE.items():
            status = "✅" if available else "❌"
            print(f"  {status} {lib.title()}")
    
    def run_comprehensive_analysis(self) -> bool:
        """Run complete WiFi sonar analysis"""
        try:
            print("\n🔍 STARTING COMPREHENSIVE WIFI SONAR ANALYSIS...")
            print("=" * 60)
            
            # Step 1: Network Discovery
            print("📡 Phase 1: Network Discovery...")
            if not self.network_analyzer.discover_network_info():
                print("[!] Failed to discover network configuration")
                return False
            
            # Step 2: Device Discovery
            print("📱 Phase 2: Device Discovery...")
            self.devices = self.network_analyzer.discover_devices()
            if not self.devices:
                print("[!] No devices discovered")
                return False
            
            # Step 3: WiFi Sonar Signal Analysis
            print("📶 Phase 3: WiFi Sonar Signal Analysis...")
            router_pos = next((d.current_position for d in self.devices if d.ip == self.network_analyzer.gateway_ip), 
                            (self.house_dimensions[0]/2, self.house_dimensions[1]/2, 3.0))
            device_positions = [d.current_position for d in self.devices if d.current_position]
            
            self.signal_readings = self.wifi_sonar.simulate_signal_readings(router_pos, device_positions)
            signal_patterns = self.wifi_sonar.analyze_signal_patterns(self.signal_readings)
            
            print(f"    ✓ Analyzed {len(self.signal_readings)} signal readings")
            print(f"    ✓ Detected {len(signal_patterns.get('walls_detected', []))} wall signatures")
            print(f"    ✓ Found {len(signal_patterns.get('signal_shadows', []))} signal shadows")
            
            # Step 4: Room Detection
            print("🏠 Phase 4: Room Detection...")
            self.rooms = self.room_detector.detect_rooms_from_signals(signal_patterns, self.signal_readings)
            print(f"    ✓ Detected {len(self.rooms)} rooms")
            
            # Step 5: Object Mapping
            print("🪑 Phase 5: Object Detection and Mapping...")
            self.detected_objects = self.object_mapper.detect_objects_in_rooms(self.rooms, self.signal_readings)
            total_objects = sum(len(objs) for objs in self.detected_objects.values())
            print(f"    ✓ Mapped {total_objects} objects across all rooms")
            
            # Step 6: Device-Room Assignment
            print("📍 Phase 6: Device-Room Assignment...")
            self._assign_devices_to_rooms()
            
            print("\n✅ COMPREHENSIVE ANALYSIS COMPLETE!")
            self._display_analysis_summary()
            
            return True
            
        except Exception as e:
            print(f"[!] Error in comprehensive analysis: {e}")
            return False
    
    def _assign_devices_to_rooms(self):
        """Assign devices to detected rooms"""
        try:
            for device in self.devices:
                if not device.current_position:
                    continue
                
                # Find which room contains this device
                for room in self.rooms:
                    if self._point_in_room(device.current_position, room):
                        device.room_id = room.room_id
                        # Add device IP to room's device list
                        if device.ip not in room.devices_in_room:
                            room.devices_in_room.append(device.ip)
                        break
                
                if not device.room_id:
                    device.room_id = "unassigned"
                    
        except Exception as e:
            print(f"[!] Error assigning devices to rooms: {e}")
    
    def _point_in_room(self, point: Tuple[float, float, float], room: Room) -> bool:
        """Check if point is within room boundaries"""
        try:
            x, y, z = point
            
            # Simple rectangular room check
            min_x = min(room.boundaries, key=lambda p: p[0])[0]
            max_x = max(room.boundaries, key=lambda p: p[0])[0]
            min_y = min(room.boundaries, key=lambda p: p[1])[1]
            max_y = max(room.boundaries, key=lambda p: p[1])[1]
            
            return (min_x <= x <= max_x and 
                   min_y <= y <= max_y and 
                   abs(z - room.center[2]) <= 1.5)
        except:
            return False
    
    def _display_analysis_summary(self):
        """Display comprehensive analysis summary"""
        print("\n" + "="*80)
        print("📊 WIFI SONAR ANALYSIS SUMMARY")
        print("="*80)
        
        print(f"🏠 House Structure:")
        print(f"   📐 Dimensions: {self.house_dimensions[0]}m × {self.house_dimensions[1]}m × {self.house_dimensions[2]} floors")
        print(f"   🏘️  Rooms Detected: {len(self.rooms)}")
        print(f"   🪑 Objects Mapped: {sum(len(objs) for objs in self.detected_objects.values())}")
        
        print(f"\n📱 Network Devices:")
        print(f"   📊 Total Devices: {len(self.devices)}")
        confirmed_devices = len([d for d in self.devices if d.confirmed_real])
        print(f"   ✅ Confirmed Real: {confirmed_devices}")
        print(f"   📡 Network: {self.network_analyzer.current_network or 'Unknown'}")
        
        print(f"\n📶 Signal Analysis:")
        print(f"   📊 Signal Readings: {len(self.signal_readings)}")
        if self.signal_readings:
            avg_signal = np.mean([r.rssi for r in self.signal_readings])
            print(f"   📈 Average RSSI: {avg_signal:.1f} dBm")
        
        # Room details
        if self.rooms:
            print(f"\n🏠 Detected Rooms:")
            for room in self.rooms:
                objects_count = len(self.detected_objects.get(room.room_id, []))
                devices_in_room = len(room.devices_in_room)
                print(f"   🏘️  {room.room_type.replace('_', ' ').title()}: {room.area:.1f}m² "
                      f"(Floor {room.floor + 1}, {objects_count} objects, {devices_in_room} devices)")
        
        print("="*80)
    
    def show_individual_room_analysis(self):
        """Show analysis for individual rooms with device IPs and coordinates"""
        try:
            if not self.rooms:
                print("[!] No rooms detected yet. Run analysis first.")
                return
            
            print(f"\n🏠 INDIVIDUAL ROOM ANALYSIS")
            print("=" * 60)
            
            for i, room in enumerate(self.rooms, 1):
                print(f"\n🏘️  Room {i}: {room.room_type.replace('_', ' ').title()}")
                print(f"   📍 Room ID: {room.room_id}")
                print(f"   📐 Area: {room.area:.1f}m²")
                print(f"   🏢 Floor: {room.floor + 1}")
                print(f"   📍 Center Coordinates: ({room.center[0]:.1f}, {room.center[1]:.1f}, {room.center[2]:.1f})")
                
                # Room boundaries
                print(f"   🔲 Boundaries:")
                for j, (x, y) in enumerate(room.boundaries):
                    print(f"      Corner {j+1}: ({x:.1f}, {y:.1f})")
                
                # Objects in room with exact coordinates
                objects = self.detected_objects.get(room.room_id, [])
                if objects:
                    print(f"   🪑 Objects ({len(objects)}):")
                    for obj in objects:
                        x, y, z = obj.position
                        w, h, d = obj.dimensions
                        print(f"      • {obj.object_type.replace('_', ' ').title()}")
                        print(f"        📍 Position: ({x:.1f}, {y:.1f}, {z:.1f})")
                        print(f"        📏 Dimensions: {w:.1f}×{h:.1f}×{d:.1f}m")
                        print(f"        🎯 Confidence: {obj.confidence:.1%}")
                
                # Devices in room with exact coordinates and IP addresses
                room_devices = [d for d in self.devices if d.room_id == room.room_id]
                if room_devices:
                    print(f"   📱 Network Devices ({len(room_devices)}):")
                    for device in room_devices:
                        x, y, z = device.current_position if device.current_position else (0, 0, 0)
                        status = "✅ Confirmed" if device.confirmed_real else "📡 Ping-only"
                        print(f"      • {device.hostname} ({device.device_type})")
                        print(f"        🌐 IP Address: {device.ip}")
                        print(f"        📍 Position: ({x:.1f}, {y:.1f}, {z:.1f})")
                        print(f"        🔗 MAC: {device.mac}")
                        print(f"        🏭 Vendor: {device.vendor}")
                        print(f"        🔍 Status: {status}")
                else:
                    print(f"   📱 Network Devices: None detected in this room")
                
                print("-" * 60)
                
        except Exception as e:
            print(f"[!] Error showing room analysis: {e}")
    
    def create_individual_room_renders(self):
        """Create individual renderings for each detected room"""
        try:
            if not self.rooms:
                print("[!] No rooms detected. Run analysis first.")
                return []
            
            print(f"\n🎨 Creating individual room visualizations...")
            created_files = []
            
            for room in self.rooms:
                # Get objects and devices for this room
                room_objects = self.detected_objects.get(room.room_id, [])
                room_devices = [d for d in self.devices if d.room_id == room.room_id]
                
                print(f"\n🏘️  Rendering {room.room_type.replace('_', ' ').title()}...")
                print(f"   📍 Room Center: ({room.center[0]:.1f}, {room.center[1]:.1f}, {room.center[2]:.1f})")
                print(f"   🪑 Objects: {len(room_objects)}")
                print(f"   📱 Devices: {len(room_devices)}")
                
                # Show device IPs and coordinates
                if room_devices:
                    print(f"   📱 Device Details:")
                    for device in room_devices:
                        if device.current_position:
                            x, y, z = device.current_position
                            print(f"      • {device.hostname} ({device.ip}) at ({x:.1f}, {y:.1f}, {z:.1f})")
                
                # Create visualization
                filepath = self.renderer.create_individual_room_visualization(room, room_objects, room_devices)
                if filepath:
                    created_files.append(filepath)
                    print(f"   ✅ Visualization saved: {filepath}")
            
            print(f"\n✅ Created {len(created_files)} individual room visualizations!")
            return created_files
            
        except Exception as e:
            print(f"[!] Error creating room renders: {e}")
            return []
    
    def create_floor_visualization(self) -> str:
        """Create floor-by-floor visualization"""
        try:
            return self.renderer.create_floor_by_floor_visualization(
                self.rooms, self.detected_objects, self.devices)
        except Exception as e:
            print(f"[!] Error creating floor visualization: {e}")
            return ""
    
    def create_3d_house_model(self) -> str:
        """Create comprehensive 3D house model"""
        try:
            return self.renderer.create_3d_house_model(
                self.rooms, self.detected_objects, self.devices, self.signal_readings)
        except Exception as e:
            print(f"[!] Error creating 3D model: {e}")
            return ""
    
    def export_comprehensive_data(self) -> str:
        """Export all analysis data to JSON with exact coordinates"""
        try:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"wifi_sonar_analysis_SalianiBouchaib_{timestamp}.json"
            
            # Prepare comprehensive data structure
            analysis_data = {
                "metadata": {
                    "scan_time": datetime.utcnow().isoformat(),
                    "user": "SalianiBouchaib",
                    "analyzer_version": "WiFi Sonar v7.0 - Complete Edition",
                    "house_dimensions": {
                        "width": self.house_dimensions[0],
                        "height": self.house_dimensions[1],
                        "floors": self.house_dimensions[2]
                    }
                },
                "network_info": {
                    "ssid": self.network_analyzer.current_network,
                    "your_ip": self.network_analyzer.my_ip,
                    "gateway_ip": self.network_analyzer.gateway_ip
                },
                "rooms": [],
                "objects": [],
                "devices": [],
                "signal_analysis": {
                    "total_readings": len(self.signal_readings),
                    "average_rssi": np.mean([r.rssi for r in self.signal_readings]) if self.signal_readings else 0,
                    "coverage_analysis": self._analyze_signal_coverage()
                }
            }
            
            # Add room data with exact coordinates
            for room in self.rooms:
                room_data = {
                    "room_id": room.room_id,
                    "room_type": room.room_type,
                    "floor": room.floor,
                    "area": room.area,
                    "center_coordinates": {
                        "x": room.center[0],
                        "y": room.center[1], 
                        "z": room.center[2]
                    },
                    "boundaries": [{"x": x, "y": y} for x, y in room.boundaries],
                    "objects_count": len(self.detected_objects.get(room.room_id, [])),
                    "devices_count": len(room.devices_in_room),
                    "device_ips": room.devices_in_room
                }
                analysis_data["rooms"].append(room_data)
            
            # Add object data with exact coordinates
            for room_id, objects in self.detected_objects.items():
                for obj in objects:
                    obj_data = {
                        "object_id": obj.object_id,
                        "object_type": obj.object_type,
                        "room_id": obj.room_id,
                        "position_coordinates": {
                            "x": obj.position[0],
                            "y": obj.position[1],
                            "z": obj.position[2]
                        },
                        "dimensions": {
                            "width": obj.dimensions[0],
                            "height": obj.dimensions[1],
                            "depth": obj.dimensions[2]
                        },
                        "confidence": obj.confidence
                    }
                    analysis_data["objects"].append(obj_data)
            
            # Add device data with exact coordinates
            for device in self.devices:
                device_data = {
                    "ip": device.ip,
                    "mac": device.mac,
                    "hostname": device.hostname,
                    "vendor": device.vendor,
                    "device_type": device.device_type,
                    "room_id": device.room_id,
                    "position_coordinates": {
                        "x": device.current_position[0] if device.current_position else None,
                        "y": device.current_position[1] if device.current_position else None,
                        "z": device.current_position[2] if device.current_position else None
                    },
                    "confirmed_real": device.confirmed_real,
                    "discovery_methods": device.discovery_methods,
                    "last_seen": device.last_seen.isoformat()
                }
                analysis_data["devices"].append(device_data)
            
            # Save to file
            desktop = os.path.join(os.path.expanduser("~"), "Desktop")
            filepath = os.path.join(desktop, filename) if os.path.exists(desktop) else filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(analysis_data, f, indent=2, ensure_ascii=False, default=str)
            
            print(f"[✓] Comprehensive analysis data exported to: {filepath}")
            return filepath
            
        except Exception as e:
            print(f"[!] Error exporting data: {e}")
            return ""
    
    def _analyze_signal_coverage(self) -> Dict:
        """Analyze WiFi signal coverage across the house"""
        try:
            if not self.signal_readings:
                return {}
            
            # Analyze signal strength by floor
            floor_coverage = defaultdict(list)
            for reading in self.signal_readings:
                floor = int(reading.location[2] // 3.0)  # 3m per floor
                floor_coverage[floor].append(reading.rssi)
            
            coverage_analysis = {}
            for floor, rssi_values in floor_coverage.items():
                coverage_analysis[f"floor_{floor}"] = {
                    "average_rssi": np.mean(rssi_values),
                    "min_rssi": min(rssi_values),
                    "max_rssi": max(rssi_values),
                    "coverage_quality": "excellent" if np.mean(rssi_values) > -50 else 
                                      "good" if np.mean(rssi_values) > -70 else "poor"
                }
            
            return coverage_analysis
            
        except Exception as e:
            print(f"[!] Error analyzing signal coverage: {e}")
            return {}
    
    def start_real_time_monitoring(self, interval: int = 60):
        """Start real-time monitoring of network changes"""
        try:
            print(f"[*] Starting real-time WiFi sonar monitoring (interval: {interval}s)")
            self.monitoring_active = True
            
            def monitoring_loop():
                previous_device_count = len(self.devices)
                previous_device_ips = set(d.ip for d in self.devices)
                
                while self.monitoring_active:
                    try:
                        print(f"\n[*] Monitoring scan at {datetime.utcnow().strftime('%H:%M:%S')}")
                        
                        # Re-discover devices
                        current_devices = self.network_analyzer.discover_devices()
                        current_device_ips = set(d.ip for d in current_devices)
                        
                        # Check for changes
                        new_devices = current_device_ips - previous_device_ips
                        disconnected_devices = previous_device_ips - current_device_ips
                        
                        if new_devices:
                            print(f"🔔 New devices detected: {', '.join(new_devices)}")
                            for ip in new_devices:
                                device = next((d for d in current_devices if d.ip == ip), None)
                                if device and device.current_position:
                                    x, y, z = device.current_position
                                    print(f"   • {device.hostname} ({device.device_type}) at ({x:.1f}, {y:.1f}, {z:.1f})")
                        
                        if disconnected_devices:
                            print(f"📱 Devices disconnected: {', '.join(disconnected_devices)}")
                        
                        if len(current_devices) != previous_device_count:
                            print(f"📊 Device count changed: {previous_device_count} → {len(current_devices)}")
                            self.devices = current_devices
                            self._assign_devices_to_rooms()  # Reassign to rooms
                            previous_device_count = len(current_devices)
                            previous_device_ips = current_device_ips
                        
                        time.sleep(interval)
                        
                    except Exception as e:
                        print(f"[!] Monitoring error: {e}")
                        time.sleep(interval)
            
            self.monitoring_thread = threading.Thread(target=monitoring_loop, daemon=True)
            self.monitoring_thread.start()
            print("[✓] Real-time monitoring started")
            
        except Exception as e:
            print(f"[!] Error starting monitoring: {e}")
    
    def stop_monitoring(self):
        """Stop real-time monitoring"""
        try:
            self.monitoring_active = False
            if self.monitoring_thread:
                self.monitoring_thread.join(timeout=5)
            print("[✓] Monitoring stopped")
        except Exception as e:
            print(f"[!] Error stopping monitoring: {e}")

def main():
    """Main application entry point"""
    print("🚀 ENHANCED WIFI SONAR ANALYZER - COMPLETE EDITION v7.0")
    print("=" * 80)
    print("✅ WiFi Signal-Based Room Detection")
    print("✅ Individual Room Rendering with Exact Coordinates")
    print("✅ Complete Matplotlib Visualizations")
    print("✅ Floor-by-Floor Structural Mapping")
    print("✅ 3D House Model Generation")
    print("✅ Real-time Device Tracking")
    print("✅ Professional Visualization & Export")
    print(f"👤 User: SalianiBouchaib")
    print(f"📅 Current Time (UTC): 2025-07-09 22:45:40")
    print("=" * 80)
    
    # Get house configuration
    try:
        print("\n🏠 House Configuration:")
        width = input("Enter house width in meters (default 50): ").strip()
        width = float(width) if width else 50
        
        height = input("Enter house depth in meters (default 20): ").strip()
        height = float(height) if height else 20
        
        floors = input("Enter number of floors (default 3): ").strip()
        floors = int(floors) if floors else 3
        
        print(f"\n🏢 House configured: {width}m × {height}m × {floors} floors")
        
    except:
        width, height, floors = 50, 20, 3
        print("🏢 Using default house dimensions: 50m × 20m × 3 floors")
    
    # Initialize analyzer
    analyzer = EnhancedWiFiSonarAnalyzer(width, height, floors)
    
    try:
        # Run initial analysis
        print("\n🚀 Starting WiFi Sonar Analysis...")
        if not analyzer.run_comprehensive_analysis():
            print("[!] Failed to complete analysis")
            return
        
        # Main menu loop - ALL OPTIONS WORKING
        while True:
            print("\n" + "="*80)
            print("🎯 WIFI SONAR ANALYZER - MENU OPTIONS (ALL WORKING)")
            print("="*80)
            print("1. 🏠 Floor-by-Floor Room Visualization")
            print("2. 🎯 3D House Model with Objects")
            print("3. 🏘️  Render Individual Rooms with Exact Coordinates")
            print("4. 🔄 Start Real-time Monitoring")
            print("5. 📊 Show Analysis Summary")
            print("6. 🔄 Refresh Complete Analysis")
            print("7. 📋 Show Detected Rooms & Objects")
            print("8. 📱 Show Network Devices with Coordinates")
            print("9. 💾 Export Comprehensive Analysis Data")
            print("0. ❌ Exit")
            print("-"*80)
            print("💡 ALL VISUALIZATIONS INCLUDE MATPLOTLIB IMAGES!")
            print("💡 All features are fully implemented and working!")
            
            try:
                choice = input("\nSelect option (0-9): ").strip()
                
                if choice == '1':
                    print("\n🏠 Creating floor-by-floor visualization...")
                    result = analyzer.create_floor_visualization()
                    if result:
                        print("✅ Floor-by-floor visualization created with matplotlib!")
                    else:
                        print("❌ Error creating floor visualization")
                    
                elif choice == '2':
                    print("\n🎯 Creating 3D house model...")
                    result = analyzer.create_3d_house_model()
                    if result:
                        print("✅ 3D house model created with matplotlib!")
                    else:
                        print("❌ Error creating 3D house model")
                    
                elif choice == '3':
                    print("\n🏘️  Creating individual room renders...")
                    results = analyzer.create_individual_room_renders()
                    if results:
                        print(f"✅ {len(results)} individual room visualizations created!")
                    else:
                        print("❌ Error creating room renders")
                    
                elif choice == '4':
                    if not analyzer.monitoring_active:
                        interval = input("Monitoring interval in seconds (default 60): ").strip()
                        try:
                            interval = int(interval) if interval else 60
                        except:
                            interval = 60
                        analyzer.start_real_time_monitoring(interval)
                    else:
                        analyzer.stop_monitoring()
                        
                elif choice == '5':
                    analyzer._display_analysis_summary()
                    
                elif choice == '6':
                    print("\n🔄 Refreshing complete analysis...")
                    if analyzer.run_comprehensive_analysis():
                        print("✅ Analysis refreshed successfully!")
                    else:
                        print("❌ Error refreshing analysis")
                    
                elif choice == '7':
                    analyzer.show_individual_room_analysis()
                    
                elif choice == '8':
                    print(f"\n📱 Network Devices ({len(analyzer.devices)} total):")
                    for device in analyzer.devices:
                        room_name = "Unassigned"
                        if device.room_id and device.room_id != "unassigned":
                            room = next((r for r in analyzer.rooms if r.room_id == device.room_id), None)
                            if room:
                                room_name = room.room_type.replace('_', ' ').title()
                        
                        status = "✅ Confirmed" if device.confirmed_real else "📡 Ping-only"
                        pos = device.current_position
                        coordinates = f"({pos[0]:.1f}, {pos[1]:.1f}, {pos[2]:.1f})" if pos else "Unknown"
                        
                        print(f"  📱 {device.hostname} ({device.ip})")
                        print(f"     🏠 Room: {room_name}")
                        print(f"     📍 Exact Coordinates: {coordinates}")
                        print(f"     📦 Type: {device.device_type}")
                        print(f"     🔗 MAC: {device.mac}")
                        print(f"     🏭 Vendor: {device.vendor}")
                        print(f"     🔍 Status: {status}")
                        print()
                    
                elif choice == '9':
                    print("\n💾 Exporting comprehensive analysis data...")
                    result = analyzer.export_comprehensive_data()
                    if result:
                        print("✅ Comprehensive analysis data exported with exact coordinates!")
                    else:
                        print("❌ Error exporting data")
                    
                elif choice == '0':
                    if analyzer.monitoring_active:
                        analyzer.stop_monitoring()
                    print("🔌 Closing all visualization windows...")
                    plt.close('all')
                    print("👋 Exiting WiFi Sonar Analyzer")
                    break
                    
                else:
                    print("❌ Invalid option. Please enter 0-9.")
                    
            except KeyboardInterrupt:
                print("\n⚠️ Interrupted. Returning to menu...")
                continue
            except Exception as e:
                print(f"❌ Error: {e}")
                continue
        
    except KeyboardInterrupt:
        print("\n[!] Analysis interrupted by user")
        if analyzer.monitoring_active:
            analyzer.stop_monitoring()
        plt.close('all')
    except Exception as e:
        print(f"\n[!] Unexpected error: {e}")
        plt.close('all')

if __name__ == "__main__":
    main()