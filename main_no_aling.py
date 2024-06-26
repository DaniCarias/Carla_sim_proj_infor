import argparse
from setup import setup_world, environment
from spawn import spawn_sensor, spawn_vehicle
from utils.ground_truth import ground_truth_no_align as ground_truth
import carla
import queue
import cv2
import numpy as np
import open3d as o3d
import time

parser = argparse.ArgumentParser(description="Carla Dataset")
parser.add_argument('-l', '--leaf_size', type=float, help='Leaf size for downsampling', default=0.1)
args = parser.parse_args()


lidar_attributes = {
    "real_lidar": {
        'channels': '128',                      # Numero de lasers -> 128
        'range': '75.0',                        # Distancia máxima em metros -> 75.0
        'points_per_second': '2621440',         # Pontos por segundo
        'rotation_frequency': '20',             # Velocidade de rotação Hz -> 20
        'upper_fov': '45',                      # Qual o ângulo do centro para cima
        'lower_fov': '-45',                     # Qual o ângulo do centro para baixo
        'dropoff_general_rate': '0.1',          # Qual a percentagem de pontos que vai descartar -> 0.1
        'dropoff_intensity_limit': '0.8',       # O que for a baixo do valor de intensidade é descartado -> 0.8
        'dropoff_zero_intensity': '0.4',        # Se o valor de intensidade for 0 qual a percentagem de descaratar -> 0.4
        'atmosphere_attenuation_rate': '0.4',   # Atenuação da atmosfera -> 0.4
    },
}

camera_attributes = {
    "real_rgb": {
        'fov': '110',                    # Field of view horizontal em graus 110 -> Baseado na camera Zed   
        'fstop': '0.5',                  # Abertura da lente -> 1/2 -> Baseado na camera Zed
        'iso': '1900',                   # Sensitivity do sensor -> Baseado na camera Zed
        'focal_distance': '2000',        # Distância a que a profundidade do efeito de campo deve ser nítida.     
        'motion_blur_intensity': '0.2',  # Intensidade do efeito de movimento
    },
        
    "rgb_and_depth": {
        'image_size_x': '1280',
        'image_size_y': '720',
        'fov': '110',                  # Field of view horizontal em graus 110 -> Baseado na camera Zed
        'lens_k': '0',                 # Remove the distortion
        'lens_kcube': '0',             # Remove the distortion
    },
}


def lidar_transformation(extrinsic, image_queue_lidar):
    """
    The function 'lidar_transformation' transforms raw lidar data into a point cloud, applies various
    rotations and translations to fit into ground truth point cloud.
    
    :param extrinsic: Represents the extrinsic calibration matrix that describes the transformation between 
                      the lidar sensor and the camera coordinate systems. It is used to calculate the rotation
                      around the Z-axis based on the ground truth camera data.
    :param image_queue_lidar: Is the queue that holds a byte array that contains the raw lidar data.
    
    :return: The function 'lidar_transformation' returns two values:
    1. 'lidar_pcl': An Open3D PointCloud object that represents the transformed lidar point cloud.
    """
    
    lidar_pcl = o3d.geometry.PointCloud()
    
    lidar_data = image_queue_lidar.get()
    raw_data = lidar_data.raw_data
    
    point_cloud_array = np.frombuffer(raw_data, dtype=np.float32)
    point_cloud_array = np.reshape(point_cloud_array, (int(point_cloud_array.shape[0] / 4), 4))            
    point_cloud_array = np.delete(point_cloud_array, 3, 1)
    
    
# Fix the lidar point cloud transformation to world coordinates
    yaw_90 = np.array([[0, -1, 0], [1, 0, 0], [0, 0, 1]])   # Yaw = 90º
    point_cloud_array = np.dot(point_cloud_array, yaw_90) 
    
    point_cloud_array[:, 2] = -point_cloud_array[:, 2]      # Z = -Z

    
    lidar_pcl.points = o3d.utility.Vector3dVector(point_cloud_array)
    
# Transform the point cloud to the camera coordinate system
    # Rotation of 180 in the X axis
    x_180 = np.array([[1,  0,  0],
                      [0, -1,  0],
                      [0,  0, -1]])
    lidar_pcl.rotate(x_180, center=(0, 0, 0)) 
    
    # Rotation of 180 in the Y axis
    y_180 = np.array([[-1,  0,  0],
                      [ 0, -1,  0],
                      [ 0,  0,  1]])
    lidar_pcl.rotate(y_180, center=(0, 0, 0)) 
    
    # Rotation of (Extract rotation around Z-axis of the ground truth camera) in the Z axis
    theta_z = np.arctan2(extrinsic[1, 0], extrinsic[0, 0])
    z_rotation = np.array([
        [np.cos(theta_z), -np.sin(theta_z), 0],
        [np.sin(theta_z), np.cos(theta_z),  0],
        [0,               0,                1]
    ])
    lidar_pcl.rotate(z_rotation, center=(0, 0, 0))
    
    
    # Put the center of the point cloud in the origin
    centroid = np.mean(np.array(point_cloud_array), axis=0)
    point_cloud_array = point_cloud_array - centroid
    
    # ->>>>>>>>>>>>>>> TIRAR PARA CRIAR DATASET (Inrelevante para os dados) <<<<<<<<<<<<<<<<<<<<-
    point_cloud_color = np.full((len(lidar_pcl.points),3), np.array([0,0,255]))  # All points are BLUE
    lidar_pcl.colors = o3d.utility.Vector3dVector(np.clip(point_cloud_color/255, 0, 1))
    
    return lidar_pcl
        
        
def get_ground_truth(queue_list, depth_camera_list):
    """
    The function 'get_ground_truth' processes depth images from multiple cameras to generate a point cloud.
    
    :param queue_list: Dictionary containing queues for different types of depth images.
    :param depth_camera_list: Dictionary containing depth camera objects for front, right, left, and back cameras.
    
    :return: The function `ground_truth` returns three values:
    1. `points`: A numpy array containing the 3D points in the world space for all four cameras.
    2. `colors`: A numpy array containing the color information (RGB) corresponding to each 3D point.
    3. `front_extrinsic_matrix`: The extrinsic matrix corresponding to the front camera.
    """
        
    front_depth_image = queue_list['image_queue_depth_front'].get()
    right_depth_image = queue_list['image_queue_depth_right'].get()
    left_depth_image = queue_list['image_queue_depth_left'].get()
    back_depth_image = queue_list['image_queue_depth_back'].get()
    
    # Show the RGB image
    front_rbg_image = queue_list['image_queue_rgb_front'].get()
    front_rbg_image = np.reshape(np.copy(front_rbg_image.raw_data), (front_rbg_image.height, front_rbg_image.width, 4))
    cv2.imshow('RGB Camera Front Output', front_rbg_image) 

    # Get the intrinsic and extrinsic matrix of the 4 cameras
    front_intrinsic_matrix, front_extrinsic_matrix = ground_truth.get_intrinsic_extrinsic_matrix(depth_camera_list['front_depth_camera'], front_depth_image)
    right_intrinsic_matrix, right_extrinsic_matrix = ground_truth.get_intrinsic_extrinsic_matrix(depth_camera_list['right_depth_camera'], right_depth_image)
    left_intrinsic_matrix, left_extrinsic_matrix = ground_truth.get_intrinsic_extrinsic_matrix(depth_camera_list['left_depth_camera'], left_depth_image)
    back_intrinsic_matrix, back_extrinsic_matrix = ground_truth.get_intrinsic_extrinsic_matrix(depth_camera_list['back_depth_camera'], back_depth_image)

    # Get the points [[X...], [Y...], [Z...]] and the colors [[R...], [G...], [B...]]
    front_points_3D, front_color = ground_truth.point2D_to_point3D(front_depth_image, front_intrinsic_matrix)
    right_points_3D, right_color = ground_truth.point2D_to_point3D(right_depth_image, right_intrinsic_matrix)
    left_points_3D, left_color = ground_truth.point2D_to_point3D(left_depth_image, left_intrinsic_matrix)
    back_points_3D, back_color = ground_truth.point2D_to_point3D(back_depth_image, back_intrinsic_matrix)

    # To multiply by the extrinsic matrix (same shape as the extrinsic_matrix matrix)
    front_p3d = np.concatenate((front_points_3D, np.ones((1, front_points_3D.shape[1]))))
    right_p3d = np.concatenate((right_points_3D, np.ones((1, right_points_3D.shape[1]))))
    left_p3d = np.concatenate((left_points_3D, np.ones((1, left_points_3D.shape[1]))))
    back_p3d = np.concatenate((back_points_3D, np.ones((1, back_points_3D.shape[1]))))

    # Get the 3D points in the world
    front_p3d_world = np.dot(front_extrinsic_matrix, front_p3d)[:3]
    right_p3d_world = np.dot(right_extrinsic_matrix, right_p3d)[:3]
    left_p3d_world = np.dot(left_extrinsic_matrix, left_p3d)[:3]
    back_p3d_world = np.dot(back_extrinsic_matrix, back_p3d)[:3]

    # Reshape the array to (height * width, 3) -> X, Y and Z for each point
    front_p3d_world = np.transpose(front_p3d_world)
    right_p3d_world = np.transpose(right_p3d_world)
    left_p3d_world = np.transpose(left_p3d_world)
    back_p3d_world = np.transpose(back_p3d_world)
    
    points = np.concatenate((front_p3d_world, right_p3d_world, left_p3d_world, back_p3d_world))
    
# ->>>>>>>>>>>>>>> TIRAR PARA CRIAR DATASET (Inrelevante para os dados) <<<<<<<<<<<<<<<<<<<<-
    colors = np.concatenate((front_color, right_color, left_color, back_color))
        
    return points, colors, front_extrinsic_matrix


def occupancy_grid_map(points, voxel_size):
	
    min_bound = np.min(points, axis=0)
    max_bound = np.max(points, axis=0)
    
    # Compute the grid dimensions
    grid_size = np.ceil((max_bound - min_bound) / voxel_size).astype(int)
    
    # Initialize the occupancy grid
    occupancy_grid = np.zeros(grid_size, dtype=np.int8)
    
    # Convert point cloud to voxel coordinates
    # O min_bound está a fazer com que haja uma transalação para o centro do grid
    voxel_indices = np.floor((points - min_bound) / voxel_size).astype(int)
    
    # Mark the voxels as occupied
    for idx in voxel_indices:
        occupancy_grid[tuple(idx)] = 1
            
    return occupancy_grid
    

def main():
    actor_list = []
    pcl_downsampled = o3d.geometry.PointCloud()
    cc = carla.ColorConverter.LogarithmicDepth

    try:
        world, blueprint_library, traffic_manager = setup_world.setup_carla()
        
        settings = world.get_settings()
        settings.no_rendering_mode = True # No rendering mode
        settings.synchronous_mode = True  # Enables synchronous mode
        settings.fixed_delta_seconds = 0.1
        world.apply_settings(settings)

        # "DayClear" | "DayCloudy" | "DayRain" | "NigthCloudy"
        environment.weather_environment("DayClear", world)
        
        vehicle = spawn_vehicle.spawn_vehicle(world, blueprint_library)
        traffic_manager.ignore_lights_percentage(vehicle, 100)  # Ignore all the red ligths

    # Spawn cameras to get the data to the Dataset
        camera_rgb = spawn_sensor.spawn_sensores('sensor.camera.rgb', world, blueprint_library, vehicle, camera_attributes)
        camera_depth = spawn_sensor.spawn_sensores('sensor.camera.depth', world, blueprint_library, vehicle, camera_attributes)
        camera_lidar = spawn_sensor.spawn_sensores('sensor.lidar.ray_cast', world, blueprint_library, vehicle, lidar_attributes)
        print("Sensors spawned!")
        
    # Spawn cameras to get the ground truth
        front_depth_camera, front_rgb_camera, right_depth_camera, left_depth_camera, back_depth_camera = ground_truth.spawn_cameras(world, blueprint_library, vehicle, 1280, 960)
        print("Ground Truth cameras spawned!")
        
        # Add the actors to the list
        actor_list.extend([vehicle, camera_rgb, camera_depth, camera_lidar, front_depth_camera, front_rgb_camera, right_depth_camera, left_depth_camera, back_depth_camera])

    # Queues to get the data
        image_queue_rgb = queue.Queue()
        image_queue_depth = queue.Queue()
        image_queue_lidar = queue.Queue()
        # Ground Truth
        image_queue_rgb_front = queue.Queue()
        image_queue_depth_front = queue.Queue()
        image_queue_depth_right = queue.Queue()
        image_queue_depth_left = queue.Queue()
        image_queue_depth_back = queue.Queue()
        

    # Listen to the cameras
        camera_rgb.listen(image_queue_rgb.put)
        camera_depth.listen(image_queue_depth.put)
        camera_lidar.listen(image_queue_lidar.put)
        # Ground Truth
        front_rgb_camera.listen(image_queue_rgb_front.put)
        front_depth_camera.listen(image_queue_depth_front.put)
        right_depth_camera.listen(image_queue_depth_right.put)
        left_depth_camera.listen(image_queue_depth_left.put)
        back_depth_camera.listen(image_queue_depth_back.put)
        
        flag = True
        #while cv2.waitKey(1) != ord('q'):
        while flag:
            world.tick()
            flag = False
            
        # GROUND TRUTH
            queue_list = {"image_queue_rgb_front": image_queue_rgb_front, "image_queue_depth_front": image_queue_depth_front,
                          "image_queue_depth_right": image_queue_depth_right, "image_queue_depth_left": image_queue_depth_left, 
                          "image_queue_depth_back": image_queue_depth_back}
            
            depth_camera_list = {"front_depth_camera": front_depth_camera, "right_depth_camera": right_depth_camera, 
                                 "left_depth_camera": left_depth_camera, "back_depth_camera": back_depth_camera}
            
            points, colors, extrinsic = get_ground_truth(queue_list, depth_camera_list)


        # DOWNSAMPLING
            downsampled_points, downsampled_colors = ground_truth.downsample(points, colors, args.leaf_size)
            
            pcl_downsampled.points = o3d.utility.Vector3dVector(downsampled_points)
            pcl_downsampled.colors = o3d.utility.Vector3dVector(downsampled_colors)


        # LIDAR TRANSFORMATION
            lidar_pcl = lidar_transformation(extrinsic, image_queue_lidar)


        # VOXEL OCCUPANCY GRID
            voxel_occupancy_grid = occupancy_grid_map(np.array(pcl_downsampled.points), args.leaf_size)
            




    # Visualize the voxel occupancy grid
            # Find indices of occupied voxels
            occupied_indices = np.argwhere(voxel_occupancy_grid)
            # Convert voxel indices to world coordinates
            occupied_coords = occupied_indices * args.leaf_size + np.array([0, 0, 0])
            # Create Open3D point cloud from the coordinates
            point_cloud = o3d.geometry.PointCloud()
            point_cloud.points = o3d.utility.Vector3dVector(occupied_coords)
            
            o3d.visualization.draw_geometries([point_cloud])
            
            
            


            




    # SAVE THE DATA
            print(f"\nSaving data...")
        # Save the RGB image
            image = image_queue_rgb.get()
            image.save_to_disk('_out/rgb/' + time.strftime('%Y%m%d_%H%M%S') + '_%06d' % image.frame + '.png')
        # Save the Depth image
            image = image_queue_depth.get()
            image.save_to_disk('_out/depth/' + time.strftime('%Y%m%d_%H%M%S') + '_%06d' % image.frame + '.png', cc)
        # Save the Lidar point cloud
            o3d.io.write_point_cloud(f'./_out/lidar/' + time.strftime('%Y%m%d_%H%M%S') + '_%06d' % image.frame + '.ply', lidar_pcl)
        # Save the Ground Truth point cloud
            # o3d.io.write_point_cloud(f'./_out/ground_truth/' + time.strftime('%Y%m%d_%H%M%S') + '_%06d' % image.frame + '.ply', pcl_downsampled)
            np.save('_out/ground_truth/' + time.strftime('%Y%m%d_%H%M%S') + '_%06d' % image.frame + '.npy', voxel_occupancy_grid)  # Save as .npy
            np.savez_compressed('_out/ground_truth/' + time.strftime('%Y%m%d_%H%M%S') + '_%06d' % image.frame + '.npz', voxel_occupancy_grid) # Save as compressed .npz

            o3d.visualization.draw_geometries([pcl_downsampled]) #lidar_pcl
        

    finally:
        for actor in actor_list:
            actor.destroy()
        print(f"All cleaned up!")

if __name__ == '__main__':
    main()