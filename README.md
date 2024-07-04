CHANGE THE LOADED MAP WHEN RUN CARLA SERVER: "DefaultEngine.ini" and change the map in some lines

<!-- ABOUT THE PROJECT -->
## About The Project

The main objective of this project is to generate datasets for machine learning with RGB images, depth images, point clouds from a LiDAR, and voxel occupancy grids to ground truth.

**This repository explores:**
* The creation of ground truth of the 3D environment in a voxel occupancy grid, based on depth images.
* Fix the LiDAR coordinates system.
* Fix the alignment of the PCL from LiDAR with the ground truth
* Creating routes for the vehicle to travel
* Generate dataset with point clouds of segmentation


## Create the ground truth from depth images

The method chosen to obtain the ground truth was based on depth images. 
Since the Carla Sim does not allow for a 360º FOV in the depth camera, it was decided to use 4 cameras with a 90º FOV. In this way, the 4 cameras are positioned to cover 360º.

### Intrinsic parameters
To transform the depth image into a point cloud, it was necessary to obtain the camera's intrinsic parameters to convert the coordinates of the image pixels into 3D coordinates. These intrinsic parameters include the focal length, optical center, and distortion coefficients, and are essential for calculating the exact position of each point in 3D space from the depth data.

### Extrinsic parameters
To describe the position and orientation of the camera in 3D space, we needed the extrinsic parameters, which provide information on how the camera is positioned and oriented about the coordinate system. The extrinsic matrix contains information about the rotation and translation of the points in the point cloud.

### Get the depth (Z axis)
To obtain the normalized depth [0, 1] of each pixel, of each image, the mathematical function was used:

$P(u,v) = \frac{R + G * 256 + B * 256 * 256}{256 * 256 * 256 - 1}$

Next, the depth values were converted to meters, and the points with depths of less than 90 meters were selected.

### Get the (X, Y, Z) coordinates
From the respective depth values and the intrinsic matrix of the matrix, they were converted into 3D points (X, Y and Z).
To transform the points into 3 dimensions, the following mathematical function is applied the following mathematical function:

![image](https://github.com/DaniCarias/Carla_sim_proj_infor/assets/93714772/021c26f8-1af7-4e2f-ad72-acaabd7ea055)

Where "x" and "y" are the coordinates of the image pixels, "fl" is the focal length, "c" is the center of the image and "p" are the previously calculated depth values corresponding to each pixel.

The result of these operations is a matrix of points with the coordinates x, y and z.

### Camera to word
To locate the 4 point clouds in 3D space, in order to create a 360º view, we had to multiply the resulting matrix by the extrinsic matrix of each camera in order to obtain the rotation and translation that each point cloud needs in order to be correctly located in relation to its origin (camera).


**Obtaining the following result:**
![ground_truth_90](https://github.com/DaniCarias/Carla_sim_proj_infor/assets/93714772/b41fc829-3acb-4481-866f-9153c04876b5)
![ground_truth_360](https://github.com/DaniCarias/Carla_sim_proj_infor/assets/93714772/cc2cc3c0-5765-4405-96bd-f38ffb996033)








