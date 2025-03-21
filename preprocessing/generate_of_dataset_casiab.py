import cv2
import numpy as np
import argparse
import os
import warnings
import glob

# Fix for numpy versions where ComplexWarning is missing
if not hasattr(np, 'ComplexWarning'):
    class ComplexWarning(Warning):
        pass
    np.ComplexWarning = ComplexWarning

# Fix for deepdish expecting np.object
np.object = object  # Required for deepdish compatibility

import deepdish as dd

#Load video from set of frames
def loadVideo(video_path):
	frame_list = sorted(glob.glob(os.path.join(video_path, '*.png')))
	if len(frame_list) > 0:
		frames = []
		for frame_file in frame_list:
			# Load frame-by-frame
			frame = cv2.imread(frame_file)
			frame = np.expand_dims(frame, axis=0)
			frames.append(frame)

		return np.vstack(frames)
	else:
		return None

# Prepare input
# Input arguments
parser = argparse.ArgumentParser(description='Build OF train dataset.')

parser.add_argument('--ofdir', type=str, required=False,
                    default='CASIAB_pre/',
					help='Full path to of directory')

parser.add_argument('--outdir', type=str, required=False,
                    default='CASIAB_tf_pre/',
                    help="Full path for output files. Note that one or more folders are created to store de files")

args = parser.parse_args()

ofdir = args.ofdir
outdir = args.outdir

# Initialize some parameters...
np.random.seed(0)

videoId = 1
labels_ = []
videoIds_ = []
gaits_ = []
frames_ = []
bbs_ = []
file_ = []
cams_ = []
meanSample = np.zeros((64,64,3), dtype=np.float32) #OF dimension

# Subjects loop from OF folder
id_folders = sorted(glob.glob(os.path.join(ofdir, '*/')))
folder_dir = 'tfimdb_casiab_N074_train_of' + str(30) + '_64x64'  	#30 FPS?
os.makedirs(os.path.join(outdir, folder_dir), exist_ok=True)

#Subjects = 124
for id_ix in id_folders:
    
    # Subject <= 74
	if int(id_ix.split('/')[-2]) <= 74:
		# Video loop for Scenarios
		video_folders = glob.glob(os.path.join(id_ix, '*/'))
		for video_ix in video_folders:
			# Camera loop for Views
			camera_folders = glob.glob(os.path.join(video_ix, '*/'))
			for camera_ix in camera_folders:
				# Load files.
				im = loadVideo(camera_ix)

				if im is not None:
					# Stack n_frames continuous frames
					id = int(id_ix.split('/')[-2])

					pattern_video = video_ix.split('/')[-2]
					pattern_camera = camera_ix.split('/')[-2]

					gait_ = pattern_video.split('-')[0]
					if gait_ == 'nm':
						gait_ = 0
					elif gait_ == 'bg':
						gait_ = 1
					elif gait_ == 'cl':
						gait_ = 2

					outpath = os.path.join(outdir, folder_dir, "{:03d}".format(id) + '_' + pattern_video + '_' + pattern_camera + '.h5')
					positions = list(range(im.shape[0]))
					# Write output file.
					data = dict()
					data['data'] = np.uint8(im)
					data['label'] = np.uint16(id)
					data['videoId'] = np.uint16(videoId)
					data['gait'] = np.uint8(gait_)
					data['frames'] = np.uint16(positions)
					data['bbs'] = np.uint8([])
					data['cams'] = np.uint8(pattern_camera)
					data['compressFactor'] = np.uint8(0)
					meanSample = meanSample + np.sum(im, axis=0)
					dd.io.save(outpath, data)

					# Append data for the global file
					labels_.append(id)
					videoIds_.append(videoId)
					gaits_.append(gait_)
					cams_.append(np.uint8(pattern_camera))
					bbs_.append([])
					frames_.append(positions)
					file_.append("{:03d}".format(id) + '_' + pattern_video + '_' + pattern_camera + '.h5')

					videoId = videoId + 1

# Get train/val/test sets.
set_ = np.ones(len(labels_))

# Write global file
data = dict()
data['label'] = np.uint16(np.asarray(labels_))
data['videoId'] = np.uint16(np.asarray(videoIds_))
data['gait'] = np.uint8(np.asarray(gaits_))
data['cam'] = np.uint8(np.asarray(cams_))
data['set'] = np.uint8(set_)
data['frames'] = frames_
data['bbs'] = bbs_
data['compressFactor'] = np.uint8(0)
data['file'] = file_
data['shape'] = (60, 60, 30)	#???
data['mean'] = meanSample / np.float32(len(labels_))
outpath = os.path.join(outdir, folder_dir + '.h5')
dd.io.save(outpath, data)
