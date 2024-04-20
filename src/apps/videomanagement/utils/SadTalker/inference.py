from glob import glob
import shutil
import torch
from time import  strftime
import os, sys, time
from argparse import ArgumentParser

from .src.utils.preprocess import CropAndExtract
from .src.test_audio2coeff import Audio2Coeff
from .src.facerender.animate import AnimateFromCoeff
from .src.generate_batch import get_data
from .src.generate_facerender_batch import get_facerender_data
from .src.utils.init_path import init_path
from .src.facerender.pirender_animate import AnimateFromCoeff_PIRender


def lip(source_image,   result_dir = './results', pose_style= 0 , cpu=False, batch_size = 2, input_yaw = None,
        input_pitch = None, input_roll = None, ref_eyeblink = None, ref_pose = None, checkpoint_dir = './checkpoints',
        preprocess = 'crop', still = True, size = 256, verbose = True, enhancer = None, background_enhancer = None,
        expression_scale = 1, driven_audio = './examples/driven_audio/bus_chinese.wav', old_version = None,
        face3dvis = None, facerender = 'facevid2vid'):

    #torch.backends.cudnn.enabled = False
    if torch.cuda.is_available() and not cpu:
        device = "cuda"
    else:
        device = "cpu"



    pic_path = source_image
    audio_path = driven_audio
    save_dir = os.path.join(result_dir, strftime("%Y_%m_%d_%H.%M.%S"))
    os.makedirs(save_dir, exist_ok=True)
    pose_style = pose_style
    batch_size = batch_size
    input_yaw_list = input_yaw
    input_pitch_list = input_pitch
    input_roll_list = input_roll
    ref_eyeblink = ref_eyeblink
    ref_pose = ref_pose

    current_root_path = os.path.split(sys.argv[0])[0]

    sadtalker_paths = init_path(checkpoint_dir, os.path.join(current_root_path, 'videomanagement/utils/SadTalker/src/config'), size, old_version,
                                preprocess)

    #init model
    preprocess_model = CropAndExtract(sadtalker_paths, device)

    audio_to_coeff = Audio2Coeff(sadtalker_paths,  device)

    if facerender == 'facevid2vid':
        animate_from_coeff = AnimateFromCoeff(sadtalker_paths, device)
    elif facerender == 'pirender':
        animate_from_coeff = AnimateFromCoeff_PIRender(sadtalker_paths, device)
    else:
        raise (RuntimeError('Unknown model: {}'.format(facerender)))




    #crop image and extract 3dmm from image
    first_frame_dir = os.path.join(save_dir, 'first_frame_dir')
    os.makedirs(first_frame_dir, exist_ok=True)
    print('3DMM Extraction for source image')
    first_coeff_path, crop_pic_path, crop_info = preprocess_model.generate(pic_path, first_frame_dir, preprocess,\
                                                                           source_image_flag=True, pic_size=size)
    if first_coeff_path is None:
        print("Can't get the coeffs of the input")
        return

    if ref_eyeblink is not None:
        ref_eyeblink_videoname = os.path.splitext(os.path.split(ref_eyeblink)[-1])[0]
        ref_eyeblink_frame_dir = os.path.join(save_dir, ref_eyeblink_videoname)
        os.makedirs(ref_eyeblink_frame_dir, exist_ok=True)
        print('3DMM Extraction for the reference video providing eye blinking')
        ref_eyeblink_coeff_path, _, _ =  preprocess_model.generate(ref_eyeblink, ref_eyeblink_frame_dir, preprocess,
                                                                   source_image_flag=False)
    else:
        ref_eyeblink_coeff_path=None

    if ref_pose is not None:
        if ref_pose == ref_eyeblink: 
            ref_pose_coeff_path = ref_eyeblink_coeff_path
        else:
            ref_pose_videoname = os.path.splitext(os.path.split(ref_pose)[-1])[0]
            ref_pose_frame_dir = os.path.join(save_dir, ref_pose_videoname)
            os.makedirs(ref_pose_frame_dir, exist_ok=True)
            print('3DMM Extraction for the reference video providing pose')
            ref_pose_coeff_path, _, _ =  preprocess_model.generate(ref_pose, ref_pose_frame_dir, preprocess,
                                                                   source_image_flag=False)
    else:
        ref_pose_coeff_path=None

    #audio2ceoff
    batch = get_data(first_coeff_path, audio_path, device, ref_eyeblink_coeff_path, still=still)
    coeff_path = audio_to_coeff.generate(batch, save_dir, pose_style, ref_pose_coeff_path)

    # 3dface render
    if face3dvis:
        from src.face3d.visualize import gen_composed_video
        gen_composed_video(device, first_coeff_path, coeff_path, audio_path, os.path.join(save_dir, '3dface.mp4'))
    
    #coeff2video
    data = get_facerender_data(coeff_path, crop_pic_path, first_coeff_path, audio_path, 
                               batch_size, input_yaw_list, input_pitch_list, input_roll_list,
                               expression_scale=expression_scale, still_mode=still, preprocess=preprocess, size=size)
    
    result = animate_from_coeff.generate(data, save_dir, pic_path, crop_info, enhancer=enhancer,
                                         background_enhancer=background_enhancer, preprocess=preprocess, img_size=size)
    
    shutil.move(result, save_dir+'.mp4')
    print('The generated video is named:', save_dir+'.mp4')

    if not verbose:
        shutil.rmtree(save_dir)

    return save_dir+'.mp4'




