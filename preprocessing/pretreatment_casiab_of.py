import os
import cv2
import numpy as np
from warnings import warn
from time import sleep
import argparse
from cvbase.optflow.visualize import flow2rgb

from multiprocessing import Pool
from multiprocessing import TimeoutError as MP_TimeoutError

START = "START"
FINISH = "FINISH"
WARNING = "WARNING"
FAIL = "FAIL"

def boolean_string(s):
	if s.upper() not in {'FALSE', 'TRUE'}:
		raise ValueError('Not a valid boolean string')
	return s.upper() == 'TRUE'


parser = argparse.ArgumentParser(description='Test')
parser.add_argument('--input_path', default='', type=str,
					help='Root path of raw silhouette dataset.')
parser.add_argument('--input_path_rgb', default='', type=str,
					help='Root path of raw RGB dataset.')
parser.add_argument('--output_path', default='', type=str,
					help='Root path for output.')
parser.add_argument('--log_file', default='./pretreatment.log', type=str,
					help='Log file path. Default: ./pretreatment.log')
parser.add_argument('--log', default=False, type=boolean_string,
					help='If set as True, all logs will be saved. '
						 'Otherwise, only warnings and errors will be saved.'
						 'Default: False')
parser.add_argument('--worker_num', default=1, type=int,
					help='How many subprocesses to use for data pretreatment. '
						 'Default: 1')
parser.add_argument('--sum_sil', default=10000, type=int,
					help='Sum of white silhouettes. ')
opt = parser.parse_args()

INPUT_PATH = opt.input_path
INPUT_PATH_RGB = opt.input_path_rgb
OUTPUT_PATH = opt.output_path
IF_LOG = opt.log
LOG_PATH = opt.log_file
WORKERS = opt.worker_num
SUM_SIL = opt.sum_sil

T_H = 64
T_W = 64

def log2str(pid, comment, logs):
	str_log = ''
	if type(logs) is str:
		logs = [logs]
	for log in logs:
		str_log += "# JOB %d : --%s-- %s\n" % (
			pid, comment, log)
	return str_log

def log_print(pid, comment, logs):
	str_log = log2str(pid, comment, logs)
	if comment in [WARNING, FAIL]:
		with open(LOG_PATH, 'a') as log_f:
			log_f.write(str_log)
	if comment in [START, FINISH]:
		if pid % 500 != 0:
			return
	print(str_log, end='')

def cut_img(img, flow, seq_info, frame_name, pid):
	# A silhouette contains too little white pixels
	# might be not valid for identification.
	if img.sum() <= SUM_SIL:
		message = 'seq:%s, frame:%s, no data, %d.' % (
			'-'.join(seq_info), frame_name, img.sum())
		warn(message)
		log_print(pid, WARNING, message)
		return None
	
 	# Get the top and bottom point
	y = img.sum(axis=1)
	y_top = (y != 0).argmax(axis=0)
	y_btm = (y != 0).cumsum(axis=0).argmax(axis=0)
	flow = flow[y_top:y_btm + 1, :, :]
	img = img[y_top:y_btm + 1, :]
	
 	# As the height of a person is larger than the width,
	# use the height to calculate resize ratio.
	_r = flow.shape[1] / flow.shape[0]
	_t_w = int(T_H * _r)
	flow = cv2.resize(flow, (_t_w, T_H), interpolation=cv2.INTER_CUBIC)
	_r = img.shape[1] / img.shape[0]
	_t_w = int(T_H * _r)
	img = cv2.resize(img, (_t_w, T_H), interpolation=cv2.INTER_CUBIC)
	
 	# Get the median of x axis and regard it as the x center of the person.
	sum_point = img.sum()
	sum_column = img.sum(axis=0).cumsum()
	x_center = -1
	for i in range(sum_column.size):
		if sum_column[i] > sum_point / 2:
			x_center = i
			break
	
 	# Prevents processing of poorly centered figures
	if x_center < 0:
		message = 'seq:%s, frame:%s, no center.' % (
			'-'.join(seq_info), frame_name)
		warn(message)
		log_print(pid, WARNING, message)
		return None
	h_T_W = int(T_W / 2)
	left = x_center - h_T_W
	right = x_center + h_T_W
	if left <= 0 or right >= img.shape[1]:
		left += h_T_W
		right += h_T_W
		_ = np.zeros((img.shape[0], h_T_W, 3))
		flow = np.concatenate([_, flow, _], axis=1)
	
	flow = flow[:, left:right, :]
	return flow.astype('float16')


def cut_pickle(seq_info, pid):
	seq_name = '-'.join(seq_info)
	log_print(pid, START, seq_name)
	seq_path = os.path.join(INPUT_PATH, *seq_info)
	seq_path_rgb = os.path.join(INPUT_PATH_RGB, *seq_info)
	out_dir = os.path.join(OUTPUT_PATH, *seq_info)
	frame_list = os.listdir(seq_path)
	frame_list.sort()
	count_frame = 0
	prev_img = None
	for _frame_name in frame_list:
		frame_path = os.path.join(seq_path, _frame_name)
		frame_path_rgb = os.path.join(seq_path_rgb, _frame_name)
		img = cv2.imread(frame_path, cv2.IMREAD_GRAYSCALE)					#silhouettes
		img_gray = cv2.imread(frame_path_rgb, cv2.IMREAD_GRAYSCALE)			#rgb to grey images
		
  		# Optical Flow Generation
		#Skip OF if there is no silhoutte from t-1 (skip the first silhouette)
		if prev_img is not None:
			#OF = Calc difference between frame t and t-1 of grey image
			flow = cv2.calcOpticalFlowFarneback(prev_img, img_gray, None, 0.5, 3, 15, 3, 5, 1.2, 0)
			flow = flow2rgb(flow) * 255
			flow = flow.astype(np.uint8)
			#Mask to get cropped / standard OF
			#cut_img return flow = None if the silhouette is not valid such as sum of white pixels <= SUM_SIL
			flow = cut_img(img, flow, seq_info, _frame_name, pid)
		else:
			flow = None

		prev_img = img_gray
  
		if flow is not None:
			# Save the cut img
			_frame_name_parts = _frame_name.split(".")
			save_path = os.path.join(out_dir, _frame_name_parts[0] + ".png")
			cv2.imwrite(save_path, flow)
			count_frame += 1
   
	# Warn if the sequence contains less than 5 frames
	if count_frame < 5:
		message = 'seq:%s, less than 5 valid data.' % (
			'-'.join(seq_info))
		warn(message)
		log_print(pid, WARNING, message)

	log_print(pid, FINISH,
			  'Contain %d valid frames. Saved to %s.'
			  % (count_frame, out_dir))


pool = Pool(WORKERS)#
results = list()
pid = 0

print('Pretreatment Start.\n'
	  'Input path: %s\n'
	  'Output path: %s\n'
	  'Log file: %s\n'
	  'Worker num: %d' % (
		  INPUT_PATH, OUTPUT_PATH, LOG_PATH, WORKERS))


# convert_videos('gray')
id_list = os.listdir(INPUT_PATH)
id_list.sort()
# Walk the input path
for _id in id_list:
	seq_type = os.listdir(os.path.join(INPUT_PATH, _id))
	seq_type.sort()
	for _seq_type in seq_type:
		view = os.listdir(os.path.join(INPUT_PATH, _id, _seq_type))
		view.sort()
		for _view in view:
			seq_info = [_id, _seq_type, _view]
			out_dir = os.path.join(OUTPUT_PATH, *seq_info)
			os.makedirs(out_dir)
			results.append(
				pool.apply_async(
					cut_pickle,
					args=(seq_info, pid)))
			sleep(0.02)
			pid += 1

pool.close()
unfinish = 1
while unfinish > 0:
	unfinish = 0
	for i, res in enumerate(results):
		try:
			res.get(timeout=0.1)
		except Exception as e:
			if type(e) == MP_TimeoutError:
				unfinish += 1
				continue
			else:
				print('\n\n\nERROR OCCUR: PID ##%d##, ERRORTYPE: %s\n\n\n',
					  i, type(e))
				raise e
pool.join()