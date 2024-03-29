import os
from os import mkdir, listdir
from shutil import move
import math
import os
from PIL import Image

data_dir = "../data"
out_dir = "../_out"

train_ratio = 0.8
val_ratio = 0.2

sensor_folders = ["rgb", "depth", "lidar"]

train_path = f"{data_dir}/train"
validation_path = f"{data_dir}/validation"

def create_folders():
    
    # Create train and test folders if they don't exist
    mkdir(train_path) if not os.path.exists(train_path) else None
    mkdir(validation_path) if not os.path.exists(validation_path) else None
    for sensor_folder in sensor_folders:
        mkdir(f"{validation_path}/{sensor_folder}") if not os.path.exists(f"{validation_path}/{sensor_folder}") else None
        mkdir(f"{train_path}/{sensor_folder}") if not os.path.exists(f"{train_path}/{sensor_folder}") else None

def create_dataset():
    # save the depth, rgb and lidar
    imgs_depth = [f for f in sorted(listdir(f"{out_dir}/depth"))]
    imgs_rgb = [f for f in sorted(listdir(f"{out_dir}/rgb"))]
    imgs_lidar = [f for f in sorted(listdir(f"{out_dir}/lidar"))]


    num_samples = min(len(imgs_depth), len(imgs_rgb), len(imgs_lidar))
    num_samples_val = math.floor(int(num_samples*val_ratio))
    num_samples_train = math.floor(int(num_samples*train_ratio))
    print(f"Total num samples of each sensor: {num_samples}")
    print(f"num_samples_validation: {num_samples_val}")
    print(f"num_samples_train: {num_samples_train}")


    imgs_val_depth = imgs_depth[:num_samples_val]
    imgs_val_rgb = imgs_rgb[:num_samples_val]
    imgs_val_lidar = imgs_lidar[:num_samples_val]
    print(f"\n-----------VALIDATION-----------")
    print(f"imgs_test_depth: {len(imgs_val_depth)}")
    print(f"imgs_test_rgb: {len(imgs_val_rgb)}")
    print(f"imgs_test_lidar: {len(imgs_val_lidar)}")


    imgs_train_depth = imgs_depth[num_samples_val:]
    imgs_train_rgb = imgs_rgb[num_samples_val:]
    imgs_train_lidar = imgs_lidar[num_samples_val:]
    print(f"\n-----------TRAIN-----------")
    print(f"imgs_train_depth: {len(imgs_train_depth)}")
    print(f"imgs_train_rgb: {len(imgs_train_rgb)}")
    print(f"imgs_train_lidar: {len(imgs_train_lidar)}")

    for image in imgs_val_depth:
        move(f"{out_dir}/depth/{image}", f"{validation_path}/depth")
    for image in imgs_val_rgb:
        move(f"{out_dir}/rgb/{image}", f"{validation_path}/rgb")
    for image in imgs_val_lidar:
        move(f"{out_dir}/lidar/{image}", f"{validation_path}/lidar")

    for image in imgs_train_depth:
        move(f"{out_dir}/depth/{image}", f"{train_path}/depth")
    for image in imgs_train_rgb:
        move(f"{out_dir}/rgb/{image}", f"{train_path}/rgb")
    for image in imgs_train_lidar:
        move(f"{out_dir}/lidar/{image}", f"{train_path}/lidar")

    print(f"\nTrain: {len(imgs_train_depth)} depth, {len(imgs_train_rgb)} rgb, {len(imgs_train_lidar)} lidar")
    print(f"Validation: {len(imgs_val_depth)} depth, {len(imgs_val_rgb)} rgb, {len(imgs_val_lidar)} lidar")
    
def set_same_num_samples():
    
    imgs_depth_after = [f for f in sorted(listdir(f"../_out/depth"))]
    imgs_rgb_after = [f for f in sorted(listdir(f"../_out/rgb"))]
    imgs_lidar_after = [f for f in sorted(listdir(f"../_out/lidar"))]
    
    num_samples = min(len(imgs_depth_after), len(imgs_rgb_after), len(imgs_lidar_after))
    
    # Remove the extra images
    for i in range(num_samples, len(imgs_depth_after)):
        os.remove(f"../_out/depth/{imgs_depth_after[i]}")
    for i in range(num_samples, len(imgs_rgb_after)):
        os.remove(f"../_out/rgb/{imgs_rgb_after[i]}")
    for i in range(num_samples, len(imgs_lidar_after)):
        os.remove(f"../_out/lidar/{imgs_lidar_after[i]}")
    
    imgs_depth = [f for f in sorted(listdir(f"../_out/depth"))]
    imgs_rgb = [f for f in sorted(listdir(f"../_out/rgb"))]
    imgs_lidar = [f for f in sorted(listdir(f"../_out/lidar"))]
    
    return len(imgs_depth), len(imgs_rgb), len(imgs_lidar)

def remove_corrupt_images():
    
    depth_dir = "../_out/depth"
    rgb_dir = "../_out/rgb"
    
    for file in os.listdir(depth_dir):
        file_path = os.path.join(depth_dir, file)
        try:
            img = Image.open(file_path) # open the image file
            img.verify() # verify that it is, in fact an image
        except (IOError, SyntaxError) as e:
            print('Bad file:', file_path) # print out the names of corrupt files
            os.remove(file_path)
            
    for file in os.listdir(rgb_dir):
        file_path = os.path.join(rgb_dir, file)
        try:
            img = Image.open(file_path) # open the image file
            img.verify() # verify that it is, in fact an image
        except (IOError, SyntaxError) as e:
            print('Bad file:', file_path) # print out the names of corrupt files
            os.remove(file_path)

    print("All corrupt images removed!")
    
    
if __name__ == "__main__":
    remove_corrupt_images()
    print("All cleaned up!")
    depth, rgb, lidar = set_same_num_samples()
    print(f"Depth: {depth} | RGB: {rgb} | Lidar: {lidar}")
    
    create_folders()
    create_dataset()
    print(f"Data as added to {train_path} and {validation_path} folders!")