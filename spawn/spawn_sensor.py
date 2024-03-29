import random
import carla
from spawn import attributes_sensores


def spawn_cameras(camera, world, blueprint_library, vehicle, img_width, img_height):
    camera_bp = blueprint_library.find(camera)
    
    if camera == 'sensor.camera.rgb':
        attributes_sensores.set_atributes_rgb(camera_bp)
    
    if camera == 'sensor.camera.depth':
        attributes_sensores.set_atributes_depth(camera_bp)
    
    # Resolução da imagem de output
    camera_bp.set_attribute('image_size_x', f"{img_width}")
    camera_bp.set_attribute('image_size_y', f"{img_height}")
    #camera_bp.set_attribute('sensor_tick', f"{1}") # Fps para os sensores estarem sync
    
    camera_transform = carla.Transform(carla.Location(x=0.9, z=1.3)) # Posição da camera em metros
    camera = world.spawn_actor(camera_bp, camera_transform, attach_to=vehicle)
    return camera



def spawn_lidar(sensor, world, blueprint_library, vehicle, attribute_type="real_lidar"):
    sensor_bp = blueprint_library.find(sensor)
    
    attributes_sensores.set_attributes_lidar(sensor_bp, attribute_type)
    
    #sensor_bp.set_attribute('sensor_tick', f"{1}") # Fps para os sensores estarem sync
    sensor_transform = carla.Transform(carla.Location(x=0, z=2.5)) # Posição do sensor em metros
    sensor = world.spawn_actor(sensor_bp, sensor_transform, attach_to=vehicle)
    return sensor