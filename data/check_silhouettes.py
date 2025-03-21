"""
import os
import cv2

def get_min_sum_in_folder(folder_path):
    min_sum = None
    for file_name in os.listdir(folder_path):
        file_path = os.path.join(folder_path, file_name)
        if os.path.isfile(file_path):
            try:
                # Replace this block with your actual sum calculation logic
                # Example: Read number from file content
                img = cv2.imread(file_path, cv2.IMREAD_GRAYSCALE)
                current_sum = img.sum()  # Sum of all pixel values
                
                # Update minimum sum
                if min_sum is None or current_sum < min_sum:
                    min_sum = current_sum
            except:
                continue  # Skip invalid files
    return min_sum

root_dir = 'silhouettes'
for root, dirs, files in os.walk(root_dir):
    # Process leaf directories (z folders)
    if not dirs:  # No subdirectories means this is a z folder
        min_sum = get_min_sum_in_folder(root)
        if min_sum is not None:
            print(f"Folder: {root} | Minimum sum: {min_sum}")
"""
import os
import cv2

def check_silhouettes(base_folder):
    results = []

    # Walk through the directory structure
    for root, dirs, files in os.walk(base_folder):
        for file in files:
            if file.endswith('.png'):
                file_path = os.path.join(root, file)
                # Read the image file using OpenCV
                img = cv2.imread(file_path, cv2.IMREAD_GRAYSCALE)
                if img is not None:
                    # Check if the image is not empty
                    if img.size == 0:
                        print(f"Warning: Image {os.path.normpath(file_path)} is empty.")
                    else:
                        # Calculate the sum of pixel values
                        pixel_sum = cv2.sumElems(img)[0]
                        # Debugging information
                        print(f"File: {os.path.normpath(file_path)}, Pixel Sum: {pixel_sum}, Image Shape: {img.shape}")
                        # Check if the sum is less than 10,000
                        results.append((os.path.normpath(file_path), pixel_sum))

    # Sort results by pixel sum in ascending order
    results.sort(key=lambda x: x[1])

    # Print the results
    for file_path, pixel_sum in results:
        print(f"File: {file_path}, Sum: {pixel_sum}")

    # Write the results to a text file
    with open('output_check_silhouettes.txt', 'w') as output_file:
        for file_path, pixel_sum in results:
            output_file.write(f"File: {file_path}, Sum: {pixel_sum}\n")

# Specify the base folder containing the silhouettes
base_folder = 'silhouettes'
check_silhouettes(base_folder)

