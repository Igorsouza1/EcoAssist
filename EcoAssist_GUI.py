# Non-code GUI platform for training and deploying object detection models: https://github.com/PetervanLunteren/EcoAssist
# Written by Peter van Lunteren
# Latest edit by Evan Hallein on 3 Jul 2023

# import packages like a christmas tree
import os
import re
import sys
import cv2
import git
import json
import math
import time
import torch
import random
import signal
import shutil
import platform
import datetime
import traceback
import subprocess
import webbrowser
import numpy as np
import PIL.ExifTags
import pandas as pd
import tkinter as tk
from tkinter import *
from pathlib import Path
from random import randint
from functools import partial
from subprocess import Popen, PIPE
import xml.etree.cElementTree as ET
from PIL import ImageTk, Image, ImageFilter
from bounding_box import bounding_box as bb
from tkinter import filedialog, ttk, messagebox as mb

# set global variables
version = "4.0"
EcoAssist_files = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

# insert pythonpath
sys.path.insert(0, os.path.join(EcoAssist_files))
sys.path.insert(0, os.path.join(EcoAssist_files, "ai4eutils"))
sys.path.insert(0, os.path.join(EcoAssist_files, "yolov5"))
sys.path.insert(0, os.path.join(EcoAssist_files, "cameratraps"))

# log pythonpath
print(sys.path)

# language settings
lang = 0
step_txt = ['Passo', 'Paso']
browse_txt = ['Procurar', 'Examinar']
cancel_txt = ["Cancelar", "Cancelar"]
change_folder_txt = ['Trocar Pasta', 'Cambiar carpeta']
view_results_txt = ['Ver Resultado', 'Ver resultados']
again_txt = ['Novamente?', 'Outra vez?']
eg_txt = ['E.g.', 'Ejem.']
new_project_txt = ["<new project>", "<nuevo proyecto>"]
warning_txt = ["Aviso", "Advertencia"]
error_txt = ["Erro", "Error"]
invalid_value_txt = ["Valor Invalido", "Valor no válido"]
perc_done_txt = ["Porcentagem concluída", "Porcentaje hecho"]
processing_txt = ["Processando", "Procesando"]
elapsed_time_txt = ["Tempo decorrido", "Tiempo transcurrido"]
remaining_time_txt = ["Tempo restante", "Tiempo restante"]
running_on_txt = ["Running on", "Funcionando en"]
of_txt = ["de", "de"]

##########################################
############# MAIN FUNCTIONS #############
##########################################

# post-process files
def postprocess(src_dir, dst_dir, thresh, sep, file_placement, sep_conf, vis, crp, yol, csv, uniquify, label_placement, data_type):
    # log
    print(f"EXECUTED: {sys._getframe().f_code.co_name}({locals()})\n")

    # PREPARE AS VARIAVEIS PARA O PROCESSAMENTO IMAGEM / VIDEO
    if data_type == "img":
        recognition_file = os.path.join(src_dir, "image_recognition_file.json")
        progress_postprocess_frame = img_progress_postprocess_frame
        progress_postprocess_progbar = img_progress_postprocess_progbar
        progress_postprocess_stats = img_progress_postprocess_stats
    else:
        recognition_file = os.path.join(src_dir, "video_recognition_file.json")
        progress_postprocess_frame = vid_progress_postprocess_frame
        progress_postprocess_progbar = vid_progress_postprocess_progbar
        progress_postprocess_stats = vid_progress_postprocess_stats

    # init vars
    global cancel_var
    start_time = time.time()
    nloop = 1
    timestamp = str(datetime.date.today()) + str(datetime.datetime.now().strftime("%H%M%S"))
    timestamp = timestamp.replace('-', '')

    # Verifica se o tipo de dado é um vídeo
    if data_type == "vid":
        # Se qualquer uma das opções de visualização, recorte ou anotação estiver ativada
        if vis or crp or yol:
            # Chama uma função para verificar a presença de um arquivo JSON necessário e, em seguida, emite um aviso ao usuário.
            # Os argumentos da função são listas que contêm mensagens em diferentes idiomas.
            check_json_presence_and_warn_user(["visualize, crop or annotate", "visualizar, recortar o anotar"][lang],
                                            ["visualizing, cropping or annotating", "visualizando, recortando o anotando"][lang],
                                            ["visualization, cropping, and annotation", "visualización, recorte y anotación"][lang])
            # Desativa as opções de visualização, recorte e anotação, definindo-as como False
            vis, crp, yol = [False] * 3

    # early exit if user specifies file movement twice (i.e., folder separation and creating folder structure with unique filenames)
    if yol and uniquify and sep:
        mb.showerror(error_txt[lang], ["It's not possible to separate folders and create unique filenames at the same time. If you want that, run the post-processing"
                                       " twice.", "No es posible separar las carpetas y crear nombres de archivo únicos al mismo tiempo. Si deseas lograr eso, ejecuta "
                                       "el procesamiento posterior dos veces."][lang])
        return

    # fetch label map
    label_map = fetch_label_map_from_json(recognition_file)
    inverted_label_map = {v: k for k, v in label_map.items()}

    # create list with colours for visualisation
    if vis:
        colors = ["fuchsia", "blue", "orange", "yellow", "green", "red", "aqua", "navy", "teal", "olive", "lime", "maroon", "purple"]
        colors = colors * 30 # colors for 390 classes
    
    # make sure json has relative paths
    json_paths_converted = False
    if check_json_paths(recognition_file) != "relative":
        make_json_relative(recognition_file)
        json_paths_converted = True
    
    # add cancel button
    cancel_var = False
    btn_cancel = Button(progress_postprocess_frame, text=cancel_txt[lang], command=cancel)
    btn_cancel.grid(row=9, column=0, columnspan=2)

    # create classes.txt
    if yol:
        classes_txt = os.path.join(dst_dir, "classes.txt")
        with open(classes_txt, 'w') as f:
            for key in label_map:
                f.write(f"{label_map[key]}\n")
    
    # open json file
    with open(recognition_file) as image_recognition_file_content:
        data = json.load(image_recognition_file_content)
    n_images = len(data['images'])

    # initialise the csv files
    if csv:
        # for files
        csv_for_files = os.path.join(dst_dir, "results_files.csv")
        if not os.path.isfile(csv_for_files):
            df = pd.DataFrame(list(), columns=["absolute_path", "relative_path", "data_type", "n_detections", "max_confidence",
                                               'datetime', 'datetime_original', 'datetime_digitized', 'make', 'shutter_speed_value',
                                               'aperture_value', 'exposure_bias_value', 'max_aperture_value', 'GPSInfo'])
            df.to_csv(csv_for_files, encoding='utf-8', index=False)
        
        # for detections
        csv_for_detections = os.path.join(dst_dir, "results_detections.csv")
        if not os.path.isfile(csv_for_detections):
            df = pd.DataFrame(list(), columns=["absolute_path", "relative_path", "data_type", "label", "confidence", "bbox_left",
                                               "bbox_top", "bbox_right", "bbox_bottom", "file_height", "file_width", 'datetime',
                                               'datetime_original', 'datetime_digitized', 'make', 'shutter_speed_value', 'aperture_value',
                                               'exposure_bias_value', 'max_aperture_value', 'GPSInfo'])
            df.to_csv(csv_for_detections, encoding='utf-8', index=False)

    # loop through images
    failure_warning_shown = False
    failure_warning_log = os.path.join(dst_dir, "failure_warning_log.txt")
    for image in data['images']:

        # cancel process if required
        if cancel_var:
            break
        
        # check for failure
        if "failure" in image:
            if not failure_warning_shown:
                mb.showwarning(warning_txt[lang], [f"One or more files failed to be analysed by the model (e.g., corrupt files) and will be skipped by "
                                                  f"post-processing features. See\n\n'{failure_warning_log}'\n\nfor more info.",
                                                  f"Uno o más archivos no han podido ser analizados por el modelo (por ejemplo, ficheros corruptos) y serán "
                                                  f"omitidos por las funciones de post-procesamiento. Para más información, véase\n\n'{failure_warning_log}'"][lang])
                failure_warning_shown = True
            
            # write warnings to log file
            with open(failure_warning_log, 'a+') as f:
                f.write(f"File '{image['file']}' was skipped by post processing features because '{image['failure']}'\n")
            f.close()

            # skip this iteration
            continue
        
        # get image info
        file = image['file']
        detections_list = image['detections']
        n_detections = len(detections_list)
        progress_postprocess_progbar['value'] += 100 / n_images

        # init vars
        max_detection_conf = 0.0
        unique_labels = []
        bbox_info = []
        csv_detectons = []
        csv_files = []

        # open files
        if vis or crp or yol or csv:
            if data_type == "img":
                im_to_vis = cv2.imread(os.path.join(src_dir, file))
                im_to_crop_path = os.path.join(src_dir, file)
                 # load old image and extract EXIF
                origImage = Image.open(os.path.join(src_dir, file))
                try:
                    exif = origImage.info['exif']
                except:
                    exif = None

                origImage.close()
            else:
                vid = cv2.VideoCapture(os.path.join(src_dir, file))

            # try to read exif data
            if csv:
                try:
                    img_for_exif = PIL.Image.open(os.path.join(src_dir, file))
                    exif_data = {
                        PIL.ExifTags.TAGS[k]: v
                        for k, v in img_for_exif._getexif().items()
                        if k in PIL.ExifTags.TAGS
                    }
                except:
                    exif_data = None
                img_for_exif.close()

                # check if datetime values can be found
                exif_params = []
                for param in ['DateTime', 'DateTimeOriginal', 'DateTimeDigitized', 'Make', 'ShutterSpeedValue', 'ApertureValue', 'ExposureBiasValue', 'MaxApertureValue', 'GPSInfo']:
                    try:
                        param_value = str(exif_data[param])
                    except:
                        param_value = "NA"
                    exif_params.append(param_value)

        # loop through detections
        for detection in image['detections']:

            # get confidence
            conf = detection["conf"]

            # write max conf
            if conf > max_detection_conf:
                max_detection_conf = conf

            # if above user specified thresh
            if conf >= thresh:

                # get detection info
                category = detection["category"]
                label = label_map[category]
                if sep:
                    unique_labels.append(label)
                    unique_labels = sorted(list(set(unique_labels)))

                # get bbox info
                if vis or crp or yol or csv:
                    if data_type == "img":
                        height, width = im_to_vis.shape[:2]
                    else:
                        height = int(vid.get(cv2.CAP_PROP_FRAME_HEIGHT))
                        width = int(vid.get(cv2.CAP_PROP_FRAME_WIDTH))

                    w_box = detection['bbox'][2]
                    h_box = detection['bbox'][3]
                    xo = detection['bbox'][0] + (w_box/2)
                    yo = detection['bbox'][1] + (h_box/2)
                    left = int(round(detection['bbox'][0] * width))
                    top = int(round(detection['bbox'][1] * height))
                    right = int(round(w_box * width)) + left
                    bottom = int(round(h_box * height)) + top

                    # store in list
                    bbox_info.append([label, conf, left, top, right, bottom, height, width, xo, yo, w_box, h_box])

        # separate files
        if sep:
            if n_detections == 0:
                file = move_files(file, "vazio", file_placement, max_detection_conf, sep_conf, dst_dir, src_dir)
            else:
                if len(unique_labels) > 1:
                    labels_str = "_".join(unique_labels)
                    file = move_files(file, labels_str, file_placement, max_detection_conf, sep_conf, dst_dir, src_dir)
                elif len(unique_labels) == 0:
                    file = move_files(file, "vazio", file_placement, max_detection_conf, sep_conf, dst_dir, src_dir)
                else:
                    file = move_files(file, label, file_placement, max_detection_conf, sep_conf, dst_dir, src_dir)
        
        # collect info to append to csv files
        if csv:
            # file info
            row = pd.DataFrame([[src_dir, file, data_type, len(bbox_info), max_detection_conf, *exif_params]])
            row.to_csv(csv_for_files, encoding='utf-8', mode='a', index=False, header=False)

            # detections info
            rows = []
            for bbox in bbox_info:
                row = [src_dir, file, data_type, *bbox[:8], *exif_params]
                rows.append(row)
            rows = pd.DataFrame(rows)
            rows.to_csv(csv_for_detections, encoding='utf-8', mode='a', index=False, header=False)
    
        # visualize images
        if vis and len(bbox_info) > 0:
            for bbox in bbox_info:
                vis_label = f"{bbox[0]} {bbox[1]}"
                color = colors[int(inverted_label_map[bbox[0]])]
                bb.add(im_to_vis, *bbox[2:6], vis_label, color)
            im = os.path.join(dst_dir, file)
            Path(os.path.dirname(im)).mkdir(parents=True, exist_ok=True)
            cv2.imwrite(im, im_to_vis)
            # load new image and save exif
            if (exif != None):
                image_new = Image.open(im)
                image_new.save(im, exif=exif)
                image_new.close()
        
        # crop images
        if crp and len(bbox_info) > 0:
            counter = 1
            for bbox in bbox_info:
                # if files have been moved
                if sep:
                    im_to_crp = Image.open(os.path.join(dst_dir,file))                    
                else:
                    im_to_crp = Image.open(im_to_crop_path)
                crp_im = im_to_crp.crop((bbox[2:6]))
                im_to_crp.close()
                filename, file_extension = os.path.splitext(file)
                im_path = os.path.join(dst_dir, filename + '_crop' + str(counter) + '_' + bbox[0] + file_extension)
                Path(os.path.dirname(im_path)).mkdir(parents=True, exist_ok=True)
                crp_im.save(im_path)
                counter += 1
                 # load new image and save exif
                if (exif != None):
                    image_new = Image.open(im_path)
                    image_new.save(im_path, exif=exif)
                    image_new.close()

        # create yolo annotations
        if yol and len(bbox_info) > 0:
            filename, file_extension = os.path.splitext(file)

            # uniquify
            if uniquify:
                # create unique filenames
                filename_dst = f"{timestamp}-{'-'.join([x for x in file.split(os.sep) if x != ''])}"
                annot_file = os.path.join(dst_dir, os.path.splitext(filename_dst)[0] + ".txt")
                
                # move files
                src = os.path.join(src_dir, file)
                dst = os.path.join(dst_dir, filename_dst)     
                if label_placement == 1: # move
                    shutil.move(src, dst)
                elif label_placement == 2: # copy
                    shutil.copy2(src, dst)
            else:
                annot_file = os.path.join(dst_dir, filename + ".txt")
            
            Path(os.path.dirname(annot_file)).mkdir(parents=True, exist_ok=True)
            with open(annot_file, 'w') as f:
                for bbox in bbox_info:
                    # correct for the non-0-index-starting default label map of MD
                    if inverted_label_map == {'animal': '1', 'pessoa': '2', 'veiculo': '3'}:
                        class_id = int(inverted_label_map[bbox[0]])-1
                    else:
                        class_id = int(inverted_label_map[bbox[0]])
                    f.write(f"{class_id} {bbox[8]} {bbox[9]} {bbox[10]} {bbox[11]}\n")

        # calculate stats
        elapsed_time_sep = str(datetime.timedelta(seconds=round(time.time() - start_time)))
        time_left_sep = str(datetime.timedelta(seconds=round(((time.time() - start_time) * n_images / nloop) - (time.time() - start_time))))
        progress_postprocess_stats['text'] = create_postprocess_lbl(elapsed_time_sep, time_left_sep, command="running")
        nloop += 1
        root.update()

    # create summary csv
    if csv:
        csv_for_summary = os.path.join(dst_dir, "results_summary.csv")
        if os.path.exists(csv_for_summary):
            os.remove(csv_for_summary)
        det_info = pd.DataFrame(pd.read_csv(csv_for_detections))
        summary = pd.DataFrame(det_info.groupby(['label', 'data_type']).size().sort_values(ascending=False).reset_index(name='n_detections'))
        summary.to_csv(csv_for_summary, encoding='utf-8', mode='w', index=False, header=True)

    # remove cancel button
    btn_cancel.grid_remove()
    
    # change json paths back, if converted earlier
    if json_paths_converted:
        make_json_absolute(recognition_file)
    
    # let the user know it's done
    progress_postprocess_stats['text'] = create_postprocess_lbl(elapsed_time_sep, time_left_sep, command="done")
    root.update()

# open progress window and initiate the post-process
def start_postprocess():
    # log
    print(f"EXECUTED: {sys._getframe().f_code.co_name}({locals()})\n")
        
    # set global variables
    global img_progress_postprocess_frame
    global vid_progress_postprocess_frame
    
    # fix user input
    src_dir = var_choose_folder.get()
    dst_dir = var_output_dir.get()
    thresh = var_thresh.get()
    sep = var_separate_files.get()
    file_placement = var_file_placement.get()
    sep_conf = var_sep_conf.get()
    vis = var_vis_files.get()
    crp = var_crp_files.get()
    yol = var_yol_files.get()
    csv = var_csv.get()
    uniquify = var_uniquify.get()
    label_placement = var_label_placement.get()

    # check which json files are present
    img_json = False
    if os.path.isfile(os.path.join(src_dir, "image_recognition_file.json")):
        img_json = True
    vid_json = False
    if os.path.isfile(os.path.join(src_dir, "video_recognition_file.json")):
        vid_json = True
    if not img_json and not vid_json:
        mb.showerror(error_txt[lang], ["No model output file present. Make sure you run step 2 before post-processing the files.",
                                       "No hay archivo de salida del modelo. Asegúrese de ejecutar el paso 2 antes de postprocesar"
                                       " los archivos."][lang])
        return
    
    # check if destination dir is valid and set to input dir if not
    if dst_dir in ["", "/", "\\", ".", "~", ":"] or not os.path.isdir(dst_dir):
        mb.showerror(["Destination folder not set", "Carpeta de destino no establecida."][lang],
                        ["Destination folder not set.\n\n You have not specified where the post-processing results should be placed or the set "
                        "folder does not exist. This is required.",
                        "Carpeta de destino no establecida. No ha especificado dónde deben colocarse los resultados del postprocesamiento o la "
                        "carpeta establecida no existe. Esto opción es obligatoria."][lang])
        return

    # warn user if the original files will be overwritten with visualized files
    if os.path.normpath(dst_dir) == os.path.normpath(src_dir) and vis and not sep:
        if not mb.askyesno(["Original images will be overwritten", "Las imágenes originales se sobrescribirán."][lang], 
                      [f"WARNING! The visualized images will be placed in the folder with the original data: '{src_dir}'. By doing this, you will overwrite the original images"
                      " with the visualized ones. Visualizing is permanent and cannot be undone. Are you sure you want to continue?",
                      f"ATENCIÓN. Las imágenes visualizadas se colocarán en la carpeta con los datos originales: '{src_dir}'. Al hacer esto, se sobrescribirán las imágenes "
                      "originales con las visualizadas. La visualización es permanente y no se puede deshacer. ¿Está seguro de que desea continuar?"][lang]):
            return
    
    # warn user if images will be moved and visualized
    if sep and file_placement == 1 and vis:
        if not mb.askyesno(["Original images will be overwritten", "Las imágenes originales se sobrescribirán."][lang], 
                      [f"WARNING! You specified to visualize the original images. Visualizing is permanent and cannot be undone. If you don't want to visualize the original "
                      f"images, please select 'Copy' as '{lbl_file_placement_txt}'. Are you sure you want to continue with the current settings?",
                      "ATENCIÓN. Ha especificado visualizar las imágenes originales. La visualización es permanente y no puede deshacerse. Si no desea visualizar las "
                      f"imágenes originales, seleccione 'Copiar' como '{lbl_file_placement_txt}'. ¿Está seguro de que desea continuar con la configuración actual?"][lang]):
            return

    # open new window with progress bar and stats
    pp_process_window = Toplevel(root)
    pp_process_window.title("Post-process progress")
    pp_process_window.geometry()

    # logo
    logo = tk.Label(pp_process_window, image=grey_bg_logo)
    logo.grid(column=0, row=0, columnspan=2, sticky='ew', pady=(5, 0))

    # add image progress
    if img_json:
        img_progress_postprocess_frame = LabelFrame(pp_process_window, text=[" Postprocessing images ", " Postprocesamiento de imágenes "][lang], pady=2, padx=5, relief='solid', highlightthickness=5, font=100, fg='darkblue')
        img_progress_postprocess_frame.configure(font=(text_font, 15, "bold"))
        img_progress_postprocess_frame.grid(column=0, row=1, columnspan=2, sticky='ew')
        img_progress_postprocess_frame.columnconfigure(0, weight=3, minsize=115)
        img_progress_postprocess_frame.columnconfigure(1, weight=1, minsize=115)
        global img_progress_postprocess_progbar
        img_progress_postprocess_progbar = ttk.Progressbar(master=img_progress_postprocess_frame, orient='horizontal', mode='determinate', length=280)
        img_progress_postprocess_progbar.grid(column=0, row=0, columnspan=2, padx=5, pady=(3,0))
        global img_progress_postprocess_stats
        img_progress_postprocess_stats = ttk.Label(master=img_progress_postprocess_frame, text=create_postprocess_lbl())
        img_progress_postprocess_stats.grid(column=0, row=1, padx=5, pady=(0,3), columnspan=2)

    # add video progress
    if vid_json:
        vid_progress_postprocess_frame = LabelFrame(pp_process_window, text=[" Postprocessing videos ", " Postprocesamiento de vídeos "][lang], pady=2, padx=5, relief='solid', highlightthickness=5, font=100, fg='darkblue')
        vid_progress_postprocess_frame.configure(font=(text_font, 15, "bold"))
        vid_progress_postprocess_frame.grid(column=0, row=2, columnspan=2, sticky='ew')
        vid_progress_postprocess_frame.columnconfigure(0, weight=3, minsize=115)
        vid_progress_postprocess_frame.columnconfigure(1, weight=1, minsize=115)
        global vid_progress_postprocess_progbar
        vid_progress_postprocess_progbar = ttk.Progressbar(master=vid_progress_postprocess_frame, orient='horizontal', mode='determinate', length=280)
        vid_progress_postprocess_progbar.grid(column=0, row=0, columnspan=2, padx=5, pady=(3,0))
        global vid_progress_postprocess_stats
        vid_progress_postprocess_stats = ttk.Label(master=vid_progress_postprocess_frame, text=create_postprocess_lbl())
        vid_progress_postprocess_stats.grid(column=0, row=1, padx=5, pady=(0,3), columnspan=2)
    
    try:
        # postprocess images
        if img_json:
            postprocess(src_dir, dst_dir, thresh, sep, file_placement, sep_conf, vis, crp, yol, csv, uniquify, label_placement, data_type = "img")

        # postprocess videos
        if vid_json:
            postprocess(src_dir, dst_dir, thresh, sep, file_placement, sep_conf, vis, crp, yol, csv, uniquify, label_placement, data_type = "vid")
        
        # complete
        complete_frame(trd_step)

        # close progress window
        pp_process_window.destroy()
    
    except Exception as error:
        # log error
        print("ERROR:\n" + str(error) + "\n\nDETAILS:\n" + str(traceback.format_exc()) + "\n\n")
        
        # show error
        mb.showerror(title=error_txt[lang],
                     message=["An error has occurred", "Ha ocurrido un error"][lang] + " (EcoAssist v" + version + "): '" + str(error) + "'.",
                     detail=traceback.format_exc())
        
        # close window
        pp_process_window.destroy()

# check data and prepare for training
def prepare_data_for_training(data_folder, prop_to_test, prop_to_val):
    # log
    print(f"EXECUTED: {sys._getframe().f_code.co_name}({locals()})\n")

    # get list of all images in dir
    data_folder = os.path.normpath(data_folder)
    files = [f for f in os.listdir(data_folder) if os.path.isfile(os.path.join(data_folder, f)) and not f.endswith(".DS_Store") and f.lower().endswith(('.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif'))]

    # calculate amounts
    total_n = len(files)
    n_test = int(total_n * prop_to_test)
    n_val = int(total_n * prop_to_val)

    # select random files
    random.shuffle(files)
    test_files = files[:n_test]
    val_files = files[n_test:n_test+n_val]
    train_files = files[n_test+n_val:]

    # remove files for previous training
    old_files = ["dataset.yaml", "train_selection.txt", "train_selection.cache", "train_selection.cache.npy", "val_selection.txt", "val_selection.cache",
                 "val_selection.cache.npy", "test_selection.txt", "test_selection.cache", "test_selection.cache.npy"]
    for filename in old_files:
        old_file = os.path.join(data_folder, filename)
        if os.path.isfile(old_file):
            os.remove(old_file)

    # write text files with images
    for elem in [[train_files, "train"], [val_files, "val"], [test_files, "test"]]:
        counter = 0
        with open(os.path.join(data_folder, elem[1] + "_selection.txt"), 'w') as f:
            for file in elem[0]:
                f.write("./" + file + "\n")
                counter += 1
        send_to_output_window(f"\nWill use {counter} images as {elem[1]}");root.update()

    # read class names
    with open(os.path.join(data_folder, "classes.txt")) as f:
        lines = f.readlines()
        names = [line.rstrip('\n') for line in lines]
    nc = len(names)

    # create dataset.yaml
    if prop_to_test == 0:
        yaml_content = f"# set paths\npath: '{data_folder}'\ntrain: ./train_selection.txt\nval: ./val_selection.txt\n\n# n classes\nnc: {nc}\n\n# class names\nnames: {names}\n"
    else:
        yaml_content = f"# set paths\npath: '{data_folder}'\ntrain: ./train_selection.txt\nval: ./val_selection.txt\ntest: ./test_selection.txt\n\n# n classes\nnc: {nc}\n\n# class names\nnames: {names}\n"
    yaml_file = os.path.join(data_folder, "dataset.yaml")
    with open(yaml_file, 'w') as f:
        f.write(yaml_content)
        send_to_output_window(f"\nWritten {yaml_file} with content:\n\n{yaml_content}\n");root.update()

# check input and execute train command
def start_training():
    # log
    print(f"EXECUTED: {sys._getframe().f_code.co_name}({locals()})\n")

    # set button states
    cancel_training_bool.set(False)
    set_buttons_to_training()

    # checkout yolov5 repo to new models
    switch_yolov5_git_to("new models")

    # build command
    send_to_output_window("Building train command...");root.update()
    command_args = []
    command_args.append(sys.executable)
    command_args.append(os.path.join(EcoAssist_files, "yolov5", "train.py"))

    # resume existing training
    if var_train_type.get() == dpd_train_type_options[lang][1]: 
        # resume from file
        checkpoint_file = var_resume_checkpoint_path.get()
        if not os.path.isfile(checkpoint_file):
            mb.showerror(error_txt[lang], message=["Please specify the last checkpoint file to resume from.",
                                                   "Por favor, especifique el último archivo de punto de control desde el que reanudar."][lang])
            set_buttons_to_idle()
            return
        command_args.append(f"--resume={checkpoint_file}")
    
        # extract output folder from checkpoint file
        results_dir =  os.path.dirname(
                            os.path.dirname(
                                os.path.dirname(
                                    os.path.dirname(
                                        os.path.normpath(
                                            checkpoint_file)))))
        
    # start new training
    elif var_train_type.get() == dpd_train_type_options[lang][0]: 
        # set retrain from
        command_args.append(f"--weights={var_learning_model_path.get()}")

        # prepare data for training
        send_to_output_window("Preparing data training set...");root.update()
        data_dir = var_annotated_data.get()
        if data_dir in ["", "/", "\\", ".", "~", ":"] or not os.path.isdir(data_dir):
            mb.showerror(error_txt[lang], message=["Please specify a directory with annotated data to train on.",
                                                   "Por favor, especifique un directorio con datos anotados para entrenar."][lang])
            set_buttons_to_idle()
            return
        prepare_data_for_training(data_dir, var_test_prop.get(), var_val_prop.get())

        # add data argument
        command_args.append(f"--data={os.path.normpath(os.path.join(data_dir, 'dataset.yaml'))}")
        
        # select gpu if available
        if var_train_gpu.get():
            send_to_output_window("Searching for GPU...");root.update()

            # for windows machines
            if torch.cuda.is_available():
                send_to_output_window("\tCUDA is available.");root.update()
                command_args.append(f"--device=0")
            else:
                send_to_output_window("\tCUDA is not available.");root.update()
                
            # for apple silicon machines
            try:
                if torch.backends.mps.is_built() and torch.backends.mps.is_available():
                    send_to_output_window("\tGPU (MPS) is available.");root.update()
                    command_args.append(f"--device=mps")
                else:
                    send_to_output_window("\tGPU (MPS) is not available.");root.update()
            except AttributeError:
                pass
        
        # number of epochs
        if not var_n_epochs.get().isdecimal() or var_n_epochs.get() == "":
            invalid_value_warning("number of epochs")
            set_buttons_to_idle()
            return
        command_args.append(f"--epochs={var_n_epochs.get()}")

        # batch size
        if no_user_input(var_batch_size):
            command_args.append("--batch-size=-1")
        elif not var_batch_size.get().isdecimal():
            invalid_value_warning("batch size")
            set_buttons_to_idle()
            return
        else:
            command_args.append(f"--batch-size={var_batch_size.get()}")

        # number of dataloader workers
        if no_user_input(var_n_workers):
            command_args.append("--workers=4")
        elif not var_n_workers.get().isdecimal():
            invalid_value_warning("number of workers")
            set_buttons_to_idle()
            return
        else:
            command_args.append(f"--workers={var_n_workers.get()}")

        # image size
        if no_user_input(var_image_size_for_training) == False:
            if not var_image_size_for_training.get().isdecimal():
                invalid_value_warning("image size")
                set_buttons_to_idle()
                return
            else:
                command_args.append(f"--img={var_image_size_for_training.get()}")
        elif var_learning_model.get() == dpd_learning_model_options[lang][0] or var_learning_model.get() == dpd_learning_model_options[lang][1]:
            # megadetector models
            command_args.append(f"--img=1280")
        
        # frozen layers
        if var_learning_model.get() == dpd_learning_model_options[lang][0] or var_learning_model.get() == dpd_learning_model_options[lang][1]:
            # megadetector models
            command_args.append(f"--freeze=12")
        elif var_learning_model.get() == dpd_learning_model_options[lang][7]:
            # custom model
            if no_user_input(var_n_freeze_layers) == False:
                if not var_n_freeze_layers.get().isdecimal():
                    invalid_value_warning("number of frozen layers")
                    set_buttons_to_idle()
                    return
                else:
                    command_args.append(f"--freeze={var_n_freeze_layers.get()}")
        
        # model architecture
        if var_learning_model.get() == dpd_learning_model_options[lang][8]:
            # from scratch
            if not var_model_architecture.get() == dpd_model_architecture_options[lang][6]:
                # not "none" selected
                command_args.append(f"--cfg={var_model_architecture_path.get()}")

        # check user input for destination folder
        results_dir = var_results_dir.get()
        if results_dir in ["", "/", "\\", ".", "~", ":"] or not os.path.isdir(results_dir):
            mb.showerror(error_txt[lang], message=["Please specify the destination directory.",
                                                   "Por favor, especifique una carpeta de destino."][lang])
            set_buttons_to_idle()
            return

        # project name
        if no_user_input(var_project_name):
            invalid_value_warning("project name", numeric = False)
            set_buttons_to_idle()
            return
        command_args.append(f"--project={var_project_name.get()}")
            
        # name of the run
        if no_user_input(var_run_name) == False:
            command_args.append(f"--name={var_run_name.get()}")

        # hyperparameter file
        if var_hyper_file_path.get() != "":
            command_args.append(f"--hyp={var_hyper_file_path.get()}")

        # cache images
        if var_cache_imgs.get():
            command_args.append(f"--cache")

        # evolve
        if var_evolve.get():
            # get n generations
            if no_user_input(var_n_generations) == False:
                if not var_n_generations.get().isdecimal():
                    invalid_value_warning("number of generations")
                    set_buttons_to_idle()
                    return
                command_args.append(f"--evolve={var_n_generations.get()}")
            else:
                command_args.append(f"--evolve=300")
    
    # change directory to the destination folder
    os.chdir(results_dir)

    # adjust command for unix OS
    if os.name != 'nt':
        command_args = "'" + "' '".join(command_args) + "'"

    # log command
    send_to_output_window(f"\ncommand_args : {command_args}\n");root.update()
    send_to_output_window("\nStarting training process...\n");root.update()

    # run command
    p = Popen(command_args,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=1,
                shell=True,
                universal_newlines=True)
    
    # read the output
    skip = False
    for line in p.stdout:

        # send to console but only update the window for the lines that matter
        send_to_output_window(line)

        # skip the model summary 
        if line.split() == ["from", "n", "params", "module", "arguments"]:
            skip = True
        if line.startswith("Model summary: "):
            skip = False

        # skip the freezing process
        if not line.startswith("freezing ") and not skip:

            # pause process for unix OS
            if os.name != 'nt':
                p.send_signal(signal.SIGSTOP)
            
            # check if user cancelled the training
            if cancel_training_bool.get():
                send_to_output_window("TRAINING CANCELLED BY USER...")
                set_buttons_to_idle()
                return
            
            # update root so that console output will be updated for the user
            root.update()

            # continue process for unix OS
            if os.name != 'nt':
                p.send_signal(signal.SIGCONT)

    # set button states
    cancel_training_bool.set(False)
    set_buttons_to_idle()

# create required files and open the LabelImg software
def start_annotation():
    # log
    print(f"EXECUTED: {sys._getframe().f_code.co_name}({locals()})\n")

    # set vars
    images_dir = var_annot_dir.get()
    classes_txt = os.path.join(images_dir, "classes.txt")

    # check if images dir is valid
    if images_dir in ["", "/", "\\", ".", "~", ":"] or not os.path.isdir(images_dir):
        mb.showerror(error_txt[lang], message=["Please specify a directory with images to annotate.",
                                               "Por favor, especifique una carpeta con imágenes para anotar."][lang])
        return

    # check if user specified classes
    if not os.path.isfile(classes_txt) and no_user_input(var_annot_classes):
        invalid_value_warning("classes", numeric = False)
        return

    # create classes.txt if required
    if not os.path.isfile(classes_txt):
        classes_list = ent_annot_classes.get().split(",")
        classes_list = [s.strip() for s in classes_list]
        with open(classes_txt, 'w') as fp:
            for elem in classes_list:
                fp.write(f"{elem}\n")

    # locate open script
    if os.name == 'nt':
        labelImg_script = os.path.join(EcoAssist_files, "EcoAssist", "label.bat")
    else:
        labelImg_script = os.path.join(EcoAssist_files, "EcoAssist", "label.command")

    # create command
    command_args = []
    command_args.append(labelImg_script)
    command_args.append(images_dir)
    command_args.append(classes_txt)

    # adjust command for unix OS
    if os.name != 'nt':
        command_args = "'" + "' '".join(command_args) + "'"
    
    # log command
    print(command_args)

    # run command
    p = Popen(command_args,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=1,
                shell=True,
                universal_newlines=True)
    for line in p.stdout:
        # log stdout and stderr
        print(line, end='')
        
        # report traceback when error
        if line.startswith("Traceback "): 
            mb.showerror(["Error opening labelImg", "Error al abrir labelImg"][lang],
            message=["An error occured while opening the annotation software labelImg. Please send an email to petervanlunteren@hotmail.com"
                    " to resolve this bug.",
                    "Se ha producido un error al abrir el software de anotación labelImg. Por favor, envíe un correo electrónico a "
                    "petervanlunteren@hotmail.com para resolver este error."][lang])

# delpoy model and create json output files 
def deploy_model(path_to_image_folder, selected_options, data_type):
    # log
    print(f"EXECUTED: {sys._getframe().f_code.co_name}({locals()})\n")
    
    # adjust variables for images or videos
    if data_type == "img":
        progress_stats = progress_img_stats
        progress_frame = progress_img_frame
        progress_progbar = progress_img_progbar
    else:
        progress_stats = progress_vid_stats
        progress_frame = progress_vid_frame
        progress_progbar = progress_vid_progbar
    
    # display loading window
    progress_stats['text'] = create_md_progress_lbl(command="load", data_type = data_type)

    # prepare variables
    chosen_folder = str(Path(path_to_image_folder))
    run_detector_batch_py = os.path.join(EcoAssist_files, "cameratraps", "detection", "run_detector_batch.py")
    image_recognition_file = os.path.join(chosen_folder, "image_recognition_file.json")
    process_video_py = os.path.join(EcoAssist_files, "cameratraps", "detection", "process_video.py")
    video_recognition_file = "--output_json_file=" + os.path.join(chosen_folder, "video_recognition_file.json")
    GPU_param = "Unknown"

    # select model based on user input via dropdown menu
    custom_model_bool = False
    if var_model.get() == dpd_options_model[lang][0]: 
        # set model file
        model_file = os.path.join(EcoAssist_files, "pretrained_models", "md_v5a.0.0.pt")
        
        # set yolov5 git to accommodate old models
        switch_yolov5_git_to("old models")
        
    elif var_model.get() == dpd_options_model[lang][1]:
        # set model file
        model_file = os.path.join(EcoAssist_files, "pretrained_models", "md_v5b.0.0.pt")
        
        # set yolov5 git to accommodate old models
        switch_yolov5_git_to("old models")
    else:
        # set model file
        model_file = var_model_path.get()
        custom_model_bool = True

        # set yolov5 git to accommodate new models
        switch_yolov5_git_to("new models")
        
        # extract classes
        label_map = extract_label_map_from_model(model_file)

        # write labelmap to separate json
        json_object = json.dumps(label_map, indent=1)
        native_model_classes_json_file = os.path.join(chosen_folder, "native_model_classes.json")
        with open(native_model_classes_json_file, "w") as outfile:
            outfile.write(json_object)
        
        # add argument to command call
        selected_options.append("--class_mapping_filename=" + native_model_classes_json_file)
            
    # create commands for Windows
    if os.name == 'nt':
        if selected_options == []:
            img_command = [sys.executable, run_detector_batch_py, model_file, chosen_folder, image_recognition_file]
            vid_command = [sys.executable, process_video_py, video_recognition_file, model_file, chosen_folder]
        else:
            img_command = [sys.executable, run_detector_batch_py, model_file, *selected_options, chosen_folder, image_recognition_file]
            vid_command = [sys.executable, process_video_py, *selected_options, video_recognition_file, model_file, chosen_folder]

     # create command for MacOS and Linux
    else:
        if selected_options == []:
            img_command = [f"'{sys.executable}' '{run_detector_batch_py}' '{model_file}' '{chosen_folder}' '{image_recognition_file}'"]
            vid_command = [f"'{sys.executable}' '{process_video_py}' '{video_recognition_file}' '{model_file}' '{chosen_folder}'"]
        else:
            selected_options = "' '".join(selected_options)
            img_command = [f"'{sys.executable}' '{run_detector_batch_py}' '{model_file}' '{selected_options}' '{chosen_folder}' '{image_recognition_file}'"]
            vid_command = [f"'{sys.executable}' '{process_video_py}' '{selected_options}' '{video_recognition_file}' '{model_file}' '{chosen_folder}'"]

    # pick one command
    if data_type == "img":
        command = img_command
    else:
        command = vid_command
    
    # log
    print(f"command:\n\n{command}\n\n")

    # prepare process and cancel method per OS
    if os.name == 'nt':
        # run windows command
        p = Popen(command,
                  stdout=subprocess.PIPE,
                  stderr=subprocess.STDOUT,
                  bufsize=1,
                  shell=True,
                  universal_newlines=True)

        # cancel button
        btn_cancel = Button(progress_frame, text=cancel_txt[lang], command=lambda: Popen(f"TASKKILL /F /PID {p.pid} /T"))
        btn_cancel.grid(row=9, column=0, columnspan=2)

    else:
        # run unix command
        p = Popen(command,
                  stdout=subprocess.PIPE,
                  stderr=subprocess.STDOUT,
                  bufsize=1,
                  shell=True,
                  universal_newlines=True,
                  preexec_fn=os.setsid)
        
        # add cancel button
        btn_cancel = Button(progress_frame, text=cancel_txt[lang], command=lambda: os.killpg(os.getpgid(p.pid), signal.SIGTERM))
        btn_cancel.grid(row=9, column=0, columnspan=2)

    
    # read output and direct to tkinter
    model_error_shown = False
    model_error_log = os.path.join(chosen_folder, "model_error_log.txt")
    for line in p.stdout:
        print(line, end='')
        
        # catch model errors
        if line.startswith("No image files found"):
            mb.showerror(["No images found", "No se han encontrado imágenes"][lang],
                        [f"There are no images found in '{chosen_folder}'. \n\nAre you sure you specified the correct folder? Or should you have"
                        " selected the option 'Include subdirectories'?",
                        f"No se han encontrado imágenes en '{chosen_folder}'. ¿Está seguro de haber especificado la carpeta correcta? ¿O debería "
                        "haber seleccionado la opción 'Incluir subdirectorios'?"][lang])
            return
        if line.startswith("No videos found"):
            mb.showerror(["No videos found", "No se han encontrado vídeos"][lang],
                        line + ["\n\nAre you sure you specified the correct folder? Or should you have selected the option 'Include subdirectories'?",
                                "\n\n¿Está seguro de haber especificado la carpeta correcta? ¿O debería haber seleccionado la opción 'Incluir subdirectorios'?"][lang])
            return
        if line.startswith("No frames extracted"):
            mb.showerror(["Could not extract frames", "No se pueden extraer fotogramas"][lang],
                        line + ["\n\nConverting the videos to .mp4 might fix the issue.",
                                "\n\nConvertir los vídeos a .mp4 podría solucionar el problema."][lang])
            return
        if "Exception:" in line:
            if not model_error_shown:
                mb.showerror(error_txt[lang], [f"There are one or more model errors. See\n\n'{model_error_log}'\n\nfor more information.",
                                               f"Hay uno o más errores de modelo. Consulte\n\n'{model_error_log}'\n\npara obtener más información."][lang])
                model_error_shown = True

            # write errors to log file
            with open(model_error_log, 'a+') as f:
                f.write(f"{line}\n")
            f.close()

        if "Warning:" in line and not '%' in line[0:4]:
            if not "could not determine MegaDetector version" in line \
                and not "no metadata for unknown detector version" in line \
                and not "using user-supplied image size" in line:
                mb.showerror(warning_txt[lang], ["Model warning:\n\n", "Advertencia de modelo:\n\n"][lang] + line)
        
        # get process stats and send them to tkinter
        if line.startswith("GPU available: False"):
            GPU_param = "CPU"
        elif line.startswith("GPU available: True"):
            GPU_param = "GPU"
        elif '%' in line[0:4]:
            
            # read stats
            times = re.search("(\[.*?\])", line)[1]
            progress_bar = re.search("^[^\/]*[^[^ ]*", line.replace(times, ""))[0]
            percentage = re.search("\d*%", progress_bar)[0][:-1]
            current_im = re.search("\d*\/", progress_bar)[0][:-1]
            total_im = re.search("\/\d*", progress_bar)[0][1:]
            elapsed_time = re.search("(?<=\[)(.*)(?=<)", times)[1]
            time_left = re.search("(?<=<)(.*)(?=,)", times)[1]
            processing_speed = re.search("(?<=,)(.*)(?=])", times)[1].strip()
            
            # order stats
            stats = create_md_progress_lbl(elapsed_time = elapsed_time,
                                            time_left = time_left,
                                            current_im = current_im,
                                            total_im = total_im,
                                            processing_speed = processing_speed,
                                            percentage = percentage,
                                            GPU_param = GPU_param,
                                            data_type = data_type,
                                            command = "running")
            
            # print stats
            progress_progbar['value'] = percentage
            progress_stats['text'] = stats
        root.update()
    
    # repeat when process is done
    progress_stats['text'] = create_md_progress_lbl(elapsed_time = elapsed_time,
                                                    time_left = time_left,
                                                    current_im = current_im,
                                                    total_im = total_im,
                                                    processing_speed = processing_speed,
                                                    percentage = percentage,
                                                    GPU_param = GPU_param,
                                                    data_type = data_type,
                                                    command = "done")
    root.update()
        
    # remove button after process is done
    btn_cancel.grid_remove()
    
    # remove frames.json file
    frames_video_recognition_file = os.path.join(chosen_folder, "video_recognition_file.frames.json")
    if os.path.isfile(frames_video_recognition_file):
        os.remove(frames_video_recognition_file)
    
    # create ecoassist metadata
    ecoassist_metadata = {"ecoassist_metadata" : {"version" : version,
                                                  "custom_model" : custom_model_bool,
                                                  "custom_model_info" : {}}}
    if custom_model_bool:
        ecoassist_metadata["ecoassist_metadata"]["custom_model_info"] = {"model_name" : os.path.basename(os.path.normpath(model_file)),
                                                                         "label_map" : label_map}
    
    # write metadata to json and make abosulte if specified
    image_recognition_file = os.path.join(chosen_folder, "image_recognition_file.json")
    video_recognition_file = os.path.join(chosen_folder, "video_recognition_file.json")
    if data_type == "img" and os.path.isfile(image_recognition_file):
        append_to_json(image_recognition_file, ecoassist_metadata)
        if var_abs_paths.get():
            make_json_absolute(image_recognition_file)
    if data_type == "vid" and os.path.isfile(video_recognition_file):
        append_to_json(video_recognition_file, ecoassist_metadata)
        if var_abs_paths.get():
            make_json_absolute(video_recognition_file)

# open progress window and initiate the model deployment
def start_deploy():
    # log
    print(f"EXECUTED: {sys._getframe().f_code.co_name}({locals()})\n")
    
    # fetch global variables
    global progress_img_frame
    global progress_vid_frame
    
    # check if user selected to process either images or videos
    if not var_process_img.get() and not var_process_vid.get():
        mb.showerror(["Nothing selected to be processed", "No se ha seleccionado nada para procesar"][lang],
                        message=["You selected neither images nor videos to be processed.",
                                 "No ha seleccionado ni imágenes ni vídeos para procesar."][lang])
        return
    
    # check if chosen folder is valid
    if var_choose_folder.get() in ["", "/", "\\", ".", "~", ":"] or not os.path.isdir(var_choose_folder.get()):
        mb.showerror(error_txt[lang],
            message=["Please specify a directory with data to be processed.",
                     "Por favor, especifique un directorio con los datos a procesar."][lang])
        return
    
    # check if checkpoint entry is valid
    if var_use_custom_img_size_for_deploy.get() and not var_image_size_for_deploy.get().isdecimal():
        mb.showerror(invalid_value_txt[lang],
                    ["You either entered an invalid value for the image size, or none at all. You can only "
                    "enter numberic characters.",
                    "Ha introducido un valor no válido para el tamaño de la imagen o no ha introducido ninguno. "
                    "Sólo puede introducir caracteres numéricos."][lang])
        return

    # check if checkpoint entry is valid
    if var_use_checkpnts.get() and not var_checkpoint_freq.get().isdecimal():
        if mb.askyesno(invalid_value_txt[lang],
                        ["You either entered an invalid value for the checkpoint frequency, or none at all. You can only "
                        "enter numberic characters.\n\nDo you want to proceed with the default value 500?",
                        "Ha introducido un valor no válido para la frecuencia del punto de control o no ha introducido ninguno. "
                        "Sólo puede introducir caracteres numéricos.\n\n¿Desea continuar con el valor por defecto 500?"][lang]):
            var_checkpoint_freq.set("500")
            ent_checkpoint_freq.config(fg='black')
        else:
            return
    
    # check if the nth frame entry is valid
    if var_not_all_frames.get() and not var_nth_frame.get().isdecimal():
        if mb.askyesno(invalid_value_txt[lang],
                        [f"You either entered an invalid value for '{lbl_nth_frame_txt[lang]}', or none at all. You can only "
                        "enter numberic characters.\n\nDo you want to proceed with the default value 10?\n\n"
                        "That means you process only 1 out of 10 frames, making the process time 10 times faster.",
                        f"Ha introducido un valor no válido para '{lbl_nth_frame_txt[lang]}', o no ha introducido ninguno. Sólo "
                        "puede introducir caracteres numéricos.\n\n¿Desea continuar con el valor por defecto 10?. Eso significa "
                        "que sólo se procesa 1 de cada 10 fotogramas, con lo que el tiempo de proceso es 10 veces más rápido."][lang]):
            var_nth_frame.set("10")
            ent_nth_frame.config(fg='black')
        else:
            return
        
    # create command for the image process to be passed on to run_detector_batch.py
    additional_img_options = ["--output_relative_filenames"]
    if not var_exclude_subs.get():
        additional_img_options.append("--recursive")
    if var_excl_detecs.get():
        additional_img_options.append("--threshold=" + str(var_md_thresh.get()))
    if var_use_checkpnts.get():
        additional_img_options.append("--checkpoint_frequency=" + var_checkpoint_freq.get())
    if var_cont_checkpnt.get():
        additional_img_options.append("--resume_from_checkpoint=" + loc_chkpnt_file)
    if var_use_custom_img_size_for_deploy.get():
        additional_img_options.append("--image_size=" + var_image_size_for_deploy.get())

    # create command for the video process to be passed on to process_video.py
    additional_vid_options = []
    if not var_exclude_subs.get():
        additional_vid_options.append("--recursive")
    if var_excl_detecs.get():
        additional_vid_options.append("--rendering_confidence_threshold=" + str(var_md_thresh.get()))
        additional_vid_options.append("--json_confidence_threshold=" + str(var_md_thresh.get()))
    if var_not_all_frames.get():
        additional_vid_options.append("--frame_sample=" + var_nth_frame.get())
    
    # open new window with progress bar and stats
    md_progress_window = Toplevel(root)
    md_progress_window.title("Deploy progress")
    md_progress_window.geometry()

    # logo
    logo = tk.Label(md_progress_window, image=grey_bg_logo)
    logo.grid(column=0, row=0, columnspan=2, sticky='ew', pady=(5, 0))

    # add image progress
    if var_process_img.get():
        progress_img_frame = LabelFrame(md_progress_window, text=[" Processando Imagens ", " Procesar imágenes "][lang], pady=2, padx=5, relief='solid', highlightthickness=5, font=100, fg='darkblue')
        progress_img_frame.configure(font=(text_font, 15, "bold"))
        progress_img_frame.grid(column=0, row=1, columnspan=2, sticky='ew')
        progress_img_frame.columnconfigure(0, weight=3, minsize=115)
        progress_img_frame.columnconfigure(1, weight=1, minsize=115)
        global progress_img_progbar
        progress_img_progbar = ttk.Progressbar(master=progress_img_frame, orient='horizontal', mode='determinate', length=280)
        progress_img_progbar.grid(column=0, row=0, columnspan=2, padx=5, pady=(3,0))
        global progress_img_stats
        progress_img_stats = ttk.Label(master=progress_img_frame, text=create_postprocess_lbl())
        progress_img_stats.grid(column=0, row=1, padx=5, pady=(0,3), columnspan=2)

    # add video progress
    if var_process_vid.get():
        progress_vid_frame = LabelFrame(md_progress_window, text=[" Processando Videos ", " Procesar vídeos "][lang], pady=2, padx=5, relief='solid', highlightthickness=5, font=100, fg='darkblue')
        progress_vid_frame.configure(font=(text_font, 15, "bold"))
        progress_vid_frame.grid(column=0, row=2, columnspan=2, sticky='ew')
        progress_vid_frame.columnconfigure(0, weight=3, minsize=115)
        progress_vid_frame.columnconfigure(1, weight=1, minsize=115)
        global progress_vid_progbar
        progress_vid_progbar = ttk.Progressbar(master=progress_vid_frame, orient='horizontal', mode='determinate', length=280)
        progress_vid_progbar.grid(column=0, row=0, columnspan=2, padx=10, pady=2)
        global progress_vid_stats
        progress_vid_stats = ttk.Label(master=progress_vid_frame, text=create_postprocess_lbl())
        progress_vid_stats.grid(column=0, row=1, columnspan=2)
    
    try:
        # process images ...
        if var_process_img.get():
            deploy_model(var_choose_folder.get(), additional_img_options, data_type = "img")
        # ... and/or videos
        if var_process_vid.get():
            deploy_model(var_choose_folder.get(), additional_vid_options, data_type = "vid")
        
        # reset window
        update_frame_states()
        
        # close progress window
        md_progress_window.destroy()

    except Exception as error:
        # log error
        print("ERROR:\n" + str(error) + "\n\nDETAILS:\n" + str(traceback.format_exc()) + "\n\n")
        
        # show error
        mb.showerror(title=error_txt[lang],
                     message=["Ocorreu um erro", "Ha ocurrido un error"][lang] + " (EcoAssist v" + version + "): '" + str(error) + "'.",
                     detail=traceback.format_exc())
        
        # reset root with new states
        reset_frame_states()
        
        # close window
        md_progress_window.destroy()

############################################
############# HELPER FUNCTIONS #############
############################################

# set button states to training
def set_buttons_to_training():
    btn_cancel_training.config(state=NORMAL)
    btn_start_training.config(state=DISABLED)

# set button states to idle
def set_buttons_to_idle():
    btn_cancel_training.config(state=DISABLED)
    btn_start_training.config(state=NORMAL)

# browse file and display result
def browse_file(var, var_short, var_path, dsp, filetype, cut_off_length, options, nrow):
    # choose file
    file = filedialog.askopenfilename(filetypes=filetype)
    
    # shorten if needed
    dsp_file = os.path.basename(file)
    if len(dsp_file) > cut_off_length:
        dsp_file = "..." + dsp_file[0 - cut_off_length + 3:]
    
    # set variables
    var_short.set(dsp_file)

    # reset to default if faulty
    if file != "":
        dsp.grid(column=0, row=nrow, sticky='e')
        var_path.set(file)
    else:
        var.set(options[0])

# switch beteen versions of yolov5 git to accommodate either old or new models
def switch_yolov5_git_to(model_type):
    # log
    print(f"EXECUTED: {sys._getframe().f_code.co_name}({locals()})\n")
    
    # checkout repo
    repository = git.Repo(os.path.join(EcoAssist_files, "yolov5"))
    if model_type == "old models":
        if platform.processor() == "arm" and os.name != "nt": # M1 and M2
            repository.git.checkout("868c0e9bbb45b031e7bfd73c6d3983bcce07b9c1")
        else:
            repository.git.checkout("c23a441c9df7ca9b1f275e8c8719c949269160d1")
    elif model_type == "new models":
        repository.git.checkout("3e55763d45f9c5f8217e4dad5ba1e6c1f42e3bf8")

# extract label map from custom model
def extract_label_map_from_model(model_file):
    # log
    print(f"EXECUTED: {sys._getframe().f_code.co_name}({locals()})")

    # import module from cameratraps dir
    from cameratraps.detection.pytorch_detector import PTDetector
            
    # load model
    label_map_detector = PTDetector(model_file, force_cpu = True)
    
    # fetch classes
    try:
        CUSTOM_DETECTOR_LABEL_MAP = {}
        for id in label_map_detector.model.names:
            CUSTOM_DETECTOR_LABEL_MAP[id] = label_map_detector.model.names[id]
    except Exception as error:
        # log error
        print("ERROR:\n" + str(error) + "\n\nDETAILS:\n" + str(traceback.format_exc()) + "\n\n")
        
        # show error
        mb.showerror(title=error_txt[lang],
                     message=["An error has occurred when trying to extract classes", "Se ha producido un error al intentar extraer las clases"][lang] +
                                " (EcoAssist v" + version + "): '" + str(error) + "'" +
                                [".\n\nWill try to proceed and produce the output json file, but post-processing features of EcoAssist will not work.",
                                 ".\n\nIntentará continuar y producir el archivo json de salida, pero las características de post-procesamiento de EcoAssist no funcionarán."][lang],
                     detail=traceback.format_exc())
    
    # delete and free up memory
    del label_map_detector
    
    # log
    print(f"Label map: {CUSTOM_DETECTOR_LABEL_MAP})\n")

    # return label map
    return CUSTOM_DETECTOR_LABEL_MAP

# fetch label map from json
def fetch_label_map_from_json(path_to_json):
    with open(path_to_json, "r") as json_file:
        data = json.load(json_file)
    label_map = data['detection_categories']
    return label_map

# check if json paths are relative or absolute
def check_json_paths(path_to_json):
    with open(path_to_json, "r") as json_file:
        data = json.load(json_file)
    path = data['images'][0]['file']
    if path.startswith(os.path.normpath(var_choose_folder.get())):
        return "absolute"
    else:
        return "relative"

# make json paths relative
def make_json_relative(path_to_json):
    if check_json_paths(path_to_json) == "absolute":
        # open
        with open(path_to_json, "r") as json_file:
            data = json.load(json_file)
        
        # adjust
        for image in data['images']:
            absolute_path = image['file']
            relative_path = absolute_path.replace(os.path.normpath(var_choose_folder.get()), "")[1:]
            image['file'] = relative_path
        
        # write
        with open(path_to_json, "w") as json_file:
            json.dump(data, json_file, indent=1)
            
# make json paths absolute
def make_json_absolute(path_to_json):
    if check_json_paths(path_to_json) == "relative":
        # open
        with open(path_to_json, "r") as json_file:
            data = json.load(json_file)
        
        # adjust
        for image in data['images']:
            relative_path = image['file']
            absolute_path = os.path.normpath(os.path.join(var_choose_folder.get(), relative_path))
            image['file'] = absolute_path
        
        # write
        with open(path_to_json, "w") as json_file:
            json.dump(data, json_file, indent=1)

# add information to json file
def append_to_json(path_to_json, object_to_be_appended):
    # open
    with open(path_to_json, "r") as json_file:
        data = json.load(json_file)
    
    # adjust
    data['info'].update(object_to_be_appended)

    # write
    with open(path_to_json, "w") as json_file:
        json.dump(data, json_file, indent=1)

# show warning for video post-processing
def check_json_presence_and_warn_user(infinitive, continuous, noun):
    # check json presence
    img_json = False
    if os.path.isfile(os.path.join(var_choose_folder.get(), "image_recognition_file.json")):
        img_json = True
    vid_json = False
    if os.path.isfile(os.path.join(var_choose_folder.get(), "video_recognition_file.json")):
        vid_json = True
    
    # show warning
    if not img_json:
        if vid_json:
            mb.showerror(error_txt[lang], [f"{noun.capitalize()} is not supported for videos.",
                                           f"{noun.capitalize()} no es compatible con vídeos."][lang])
            return True
        if not vid_json:
            mb.showerror(error_txt[lang], [f"No model output file present. Make sure you run step 2 before {continuous} the files. {noun.capitalize()} "
                                            "is only supported for images.",
                                           f"No hay archivos de salida del modelo. Asegúrese de ejecutar el paso 2 antes de {continuous} los archivos. "
                                           f"{noun.capitalize()} sólo es compatible con imágenes"][lang])
            return True
    if img_json:
        if vid_json:
            mb.showinfo(warning_txt[lang], [f"{noun.capitalize()} is not supported for videos. Will continue to only {infinitive} the images...",
                                            f"No se admiten {noun.capitalize()} para los vídeos. Continuará sólo {infinitive} las imágenes..."][lang])

# dir names for when separating on confidence
conf_dirs = {0.0 : "conf_0.0",
             0.1 : "conf_0.0-0.1",
             0.2 : "conf_0.1-0.2",
             0.3 : "conf_0.2-0.3",
             0.4 : "conf_0.3-0.4",
             0.5 : "conf_0.4-0.5",
             0.6 : "conf_0.5-0.6",
             0.7 : "conf_0.6-0.7",
             0.8 : "conf_0.7-0.8",
             0.9 : "conf_0.8-0.9",
             1.0 : "conf_0.9-1.0"}

# move files into subdirectories
def move_files(file, detection_type, var_file_placement, max_detection_conf, var_sep_conf, dst_root, src_dir):
    # log
    print(f"EXECUTED: {sys._getframe().f_code.co_name}({locals()})\n")

    # squeeze in extra dir if sorting on confidence
    if var_sep_conf and detection_type != "vazio":
        global conf_dirs
        ceiled_confidence = math.ceil(max_detection_conf * 10) / 10.0
        confidence_dir = conf_dirs[ceiled_confidence]
        new_file = os.path.join(detection_type, confidence_dir, file)
    else:
        new_file = os.path.join(detection_type, file)
    
    # set paths
    src = os.path.join(src_dir, file)
    dst = os.path.join(dst_root, new_file)
    
    # create subfolder
    Path(os.path.dirname(dst)).mkdir(parents=True, exist_ok=True)
    
    # place image or video in subfolder
    if var_file_placement == 1: # move
        shutil.move(src, dst)
    elif var_file_placement == 2: # copy
        shutil.copy2(src, dst)
        
    # return new relative file path
    return(new_file)

# indent xml files so it is human readable (thanks to ade from stack overflow)
def indent(elem, level=0):
    i = "\n" + level * "  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for elem in elem:
            indent(elem, level + 1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i

# check if checkpoint file is present and assign global variable
def check_checkpnt():
    global loc_chkpnt_file
    for filename in os.listdir(var_choose_folder.get()):
            if re.search('^checkpoint_\d+\.json$', filename):
                loc_chkpnt_file = os.path.join(var_choose_folder.get(), filename)
                return True
    mb.showinfo(["No checkpoint file found", "No se ha encontrado ningún archivo de puntos de control"][lang],
                    ["There is no checkpoint file found. Cannot continue from checkpoint file...",
                    "No se ha encontrado ningún archivo de punto de control. No se puede continuar desde el archivo de punto de control..."][lang])
    return False

# order statistics from model output and return string
def create_md_progress_lbl(elapsed_time="",
                           time_left="",
                           current_im="",
                           total_im="",
                           processing_speed="",
                           percentage="",
                           GPU_param="",
                           data_type="",
                           command=""):

    # set unit
    if data_type == "img":
        unit = ["image", "imagen"][lang]
    else:
        unit = ["frame", "fotograma"][lang]
    
    # translate processing speed 
    if "it/s" in processing_speed:
        speed_prefix = [f"{unit.capitalize()} per sec:", f"{unit.capitalize()} por seg:"][lang]
        speed_suffix = processing_speed.replace("it/s", "")
    elif "s/it" in processing_speed:
        speed_prefix = [f"Sec per {unit}: ", f"seg por {unit}:"][lang]
        speed_suffix = processing_speed.replace("s/it", "")
    else:
        speed_prefix = ""
        speed_suffix = ""
        
    # loading
    if command == "load":
        return ["Algorithm is starting up...", "El algoritmo está comenzando..."][lang]
    
    # running (OS dependant)
    if command == "running":

        # windows
        if os.name == "nt":
            tab1 = "\t" if data_type == "img" else "\t\t"
            return f"{perc_done_txt[lang]}:\t\t{percentage}%\n" \
                f"{processing_txt[lang]} {unit}:{tab1}{current_im} {of_txt[lang]} {total_im}\n" \
                f"{elapsed_time_txt[lang]}:\t\t{elapsed_time}\n" \
                f"{remaining_time_txt[lang]}:\t\t{time_left}\n" \
                f"{speed_prefix}\t\t{speed_suffix}\n" \
                f"{running_on_txt[lang]}:\t\t{GPU_param}"

        # linux
        elif sys.platform == "linux" or sys.platform == "linux2":
            return f"{perc_done_txt[lang]}:\t{percentage}%\n" \
                f"{processing_txt[lang]} {unit}:\t{current_im} {of_txt[lang]} {total_im}\n" \
                f"{elapsed_time_txt[lang]}:\t\t{elapsed_time}\n" \
                f"{remaining_time_txt[lang]}:\t\t{time_left}\n" \
                f"{speed_prefix}\t\t{speed_suffix}\n" \
                f"{running_on_txt[lang]}:\t\t{GPU_param}"

        # macos
        elif sys.platform == "darwin":
            return f"{perc_done_txt[lang]}:\t{percentage}%\n" \
                f"{processing_txt[lang]} {unit}:\t{current_im} {of_txt[lang]} {total_im}\n" \
                f"{elapsed_time_txt[lang]}:\t{elapsed_time}\n" \
                f"{remaining_time_txt[lang]}:\t{time_left}\n" \
                f"{speed_prefix}\t{speed_suffix}\n" \
                f"{running_on_txt[lang]}:\t{GPU_param}"
    
    # done
    if command == "done":
        return f"{elapsed_time_txt[lang]}:\t{elapsed_time}\n" \
            f"{speed_prefix}\t{speed_suffix}"     

# get post-processing statistics and return string
def create_postprocess_lbl(elapsed_time="", time_left="", command=""):
    # waiting
    if command == "":
        return ["In queue", "Es espera"][lang]
    
    # running
    if command == "running":
        return f"{elapsed_time_txt[lang]}:\t\t{elapsed_time}\n" \
               f"{remaining_time_txt[lang]}:\t\t{time_left}"
               
    # done
    if command == "done":
        return ["Done!\n", "¡Hecho!\n"][lang]

# browse directory
def browse_dir(var, var_short, dsp, cut_off_length, n_row, n_column, str_sticky):
    # log
    print(f"EXECUTED: {sys._getframe().f_code.co_name}({locals()})\n")

    # choose directory
    chosen_dir = filedialog.askdirectory()

    # set choice to variable
    var.set(chosen_dir)
    
    # shorten, set and grid display
    dsp_chosen_dir = chosen_dir
    if len(dsp_chosen_dir) > cut_off_length:
        dsp_chosen_dir = "..." + dsp_chosen_dir[0 - cut_off_length + 3:]
    if var == var_choose_folder:
        dsp_chosen_dir = "  " + dsp_chosen_dir
    var_short.set(dsp_chosen_dir)
    dsp.grid(column=n_column, row=n_row, sticky=str_sticky)

# load a custom yolov5 model
def model_options(self):
    # log
    print(f"EXECUTED: {sys._getframe().f_code.co_name}({locals()})\n")
   
    # if custom model is selected
    if var_model.get() == dpd_options_model[lang][2]:
        
        # choose, display and set global var
        browse_file(var_model,
                    var_model_short,
                    var_model_path,
                    dsp_model,
                    [("Yolov5 model","*.pt")],
                    30,
                    dpd_options_model[lang],
                    row_model)

    else:
        var_model_short.set("")

# view results after processing
def view_results(frame):
    # log
    print(f"EXECUTED: {sys._getframe().f_code.co_name}({locals()})")
    print(f"frame text: {frame.cget('text')}\n")
    
    # convert path separators
    chosen_folder = os.path.normpath(var_choose_folder.get())
    
    # set json paths
    image_recognition_file = os.path.join(chosen_folder, "image_recognition_file.json")
    video_recognition_file = os.path.join(chosen_folder, "video_recognition_file.json")

    # open json files at step 2
    if frame.cget('text').startswith(f' {step_txt[lang]} 2'):
        if os.path.isfile(image_recognition_file):
            open_file_or_folder(image_recognition_file)
        if os.path.isfile(video_recognition_file):
            open_file_or_folder(video_recognition_file)
    
    # open destination folder at step 3
    if frame.cget('text').startswith(f' {step_txt[lang]} 3'):
        open_file_or_folder(var_output_dir.get())

# open file or folder
def open_file_or_folder(path):
    # log
    print(f"EXECUTED: {sys._getframe().f_code.co_name}({locals()})\n")
    
    # set language var
    error_opening_results_txt = ["Error opening results", "Error al abrir los resultados"]

    # open file
    if platform.system() == 'Darwin': # mac  
        try:
            subprocess.call(('open', path))
        except:
            mb.showerror(error_opening_results_txt[lang], [f"Could not open '{path}'. You'll have to find it yourself...",
                                                           f"No se ha podido abrir '{path}'. Tendrás que encontrarlo tú mismo..."][lang])
    elif platform.system() == 'Windows': # windows
        try:
            os.startfile(path)
        except:
            mb.showerror(error_opening_results_txt[lang], [f"Could not open '{path}'. You'll have to find it yourself...",
                                                           f"No se ha podido abrir '{path}'. Tendrás que encontrarlo tú mismo..."][lang])
    else: # linux
        try:
            subprocess.call(('xdg-open', path))
        except:
            try:
                subprocess.call(('gnome-open', path))
            except:
                mb.showerror(error_opening_results_txt[lang], [f"Could not open '{path}'. Neither the 'xdg-open' nor 'gnome-open' command worked. "
                                                               "You'll have to find it yourself...",
                                                               f"No se ha podido abrir '{path}'. Ni el comando 'xdg-open' ni el 'gnome-open' funcionaron. "
                                                               "Tendrá que encontrarlo usted mismo..."][lang])

##############################################
############# FRONTEND FUNCTIONS #############
##############################################

# refresh dropdown menu options
def update_dpd_options(dpd, master, var, options, cmd, row, lbl, from_lang):

    # recreate new option menu with updated options
    dpd.grid_forget()
    index = options[from_lang].index(var.get()) # get dpd index
    var.set(options[lang][index]) # set to previous index
    dpd = OptionMenu(master, var, *options[lang], command=cmd)
    dpd.configure(width=1)
    dpd.grid(row=row, column=1, sticky='nesw', padx=5)

    # only grid model_architechture if its label is displayed
    if lbl.cget("text") == lbl_model_architecture_txt[lang] and not lbl.winfo_ismapped():
        dpd.grid_forget()

    # give it same state as its label
    dpd.config(state = str(lbl['state']))

# refresh ent texts
def update_ent_text(var, string):
    if var.get() == "":
        return
    if no_user_input(var):
        original_state = str(var['state'])
        var.config(state=NORMAL, fg='grey')
        var.delete(0, tk.END)
        var.insert(0, string)
        var.config(state=original_state)

# change language
lang = 0
def set_language(to_lang):
    global lang
    from_lang = lang

    # log
    print(f"EXECUTED: {sys._getframe().f_code.co_name}({locals()})\n")

    # set language vars
    if to_lang == "gb":
        gb_widget.config(highlightbackground="black", relief="sunken")
        es_widget.config(highlightbackground="white", relief="raised")
        lang = 0
    if to_lang == "es":
        gb_widget.config(highlightbackground="white", relief="raised")
        es_widget.config(highlightbackground="black", relief="sunken")
        lang = 1

    # update tutorial text
    lbl_tutorial.config(text=lbl_tutorial_txt[lang])

    # update tab texts
    tabControl.tab(deploy_tab, text=deploy_tab_text[lang])
    tabControl.tab(train_tab, text=train_tab_text[lang])
    tabControl.tab(annotate_tab, text=annotate_tab_text[lang])
    tabControl.tab(help_tab, text=help_tab_text[lang])
    tabControl.tab(about_tab, text=about_tab_text[lang])

    # update texts of deploy tab
    fst_step.config(text=" " + fst_step_txt[lang] + " ")
    btn_choose_folder.config(text=browse_txt[lang])
    snd_step.config(text=" " + snd_step_txt[lang] + " ")
    lbl_model.config(text=lbl_model_txt[lang])
    update_dpd_options(dpd_model, snd_step, var_model, dpd_options_model, model_options, row_model, lbl_model, from_lang)
    lbl_exclude_subs.config(text=lbl_exclude_subs_txt[lang])
    lbl_excl_detecs.config(text=lbl_excl_detecs_txt[lang])
    lbl_md_thresh.config(text=lbl_md_thresh_txt[lang])
    lbl_use_custom_img_size_for_deploy.config(text=lbl_use_custom_img_size_for_deploy_txt[lang])
    lbl_image_size_for_deploy.config(text=lbl_image_size_for_deploy_txt[lang])
    update_ent_text(ent_image_size_for_deploy, f"{eg_txt[lang]}: 640")
    lbl_abs_paths.config(text=lbl_abs_paths_txt[lang])
    lbl_process_img.config(text=lbl_process_img_txt[lang])
    img_frame.config(text=" ↳ " + img_frame_txt[lang] + " ")
    lbl_use_checkpnts.config(text="     " + lbl_use_checkpnts_txt[lang])
    lbl_checkpoint_freq.config(text="        ↳ " + lbl_checkpoint_freq_txt[lang])
    update_ent_text(ent_checkpoint_freq, f"{eg_txt[lang]}: 500")
    lbl_cont_checkpnt.config(text="     " + lbl_cont_checkpnt_txt[lang])
    lbl_process_vid.config(text=lbl_process_vid_txt[lang])
    vid_frame.config(text=" ↳ " + vid_frame_txt[lang] + " ")
    lbl_not_all_frames.config(text="     " + lbl_not_all_frames_txt[lang])
    lbl_nth_frame.config(text="        ↳ " + lbl_nth_frame_txt[lang])
    update_ent_text(ent_nth_frame, f"{eg_txt[lang]}: 10")
    btn_start_deploy.config(text=btn_start_deploy_txt[lang])
    trd_step.config(text=" " + trd_step_txt[lang] + " ")
    lbl_output_dir.config(text=lbl_output_dir_txt[lang])
    btn_output_dir.config(text=browse_txt[lang])
    lbl_separate_files.config(text=lbl_separate_files_txt[lang])
    sep_frame.config(text=" ↳ " + sep_frame_txt[lang] + " ")
    lbl_file_placement.config(text="     " + lbl_file_placement_txt[lang])
    rad_file_placement_move.config(text=["Copy", "Copiar"][lang])
    rad_file_placement_copy.config(text=["Move", "Mover"][lang])
    lbl_sep_conf.config(text="     " + lbl_sep_conf_txt[lang])
    lbl_vis_files.config(text=lbl_vis_files_txt[lang])
    lbl_crp_files.config(text=lbl_crp_files_txt[lang])
    lbl_yol_files.config(text=lbl_yol_files_txt[lang])
    annot_create_frame.config(text=" ↳ " + annot_create_frame_txt[lang] + " ")
    lbl_uniquify.config(text="     " + lbl_uniquify_txt[lang])
    lbl_label_placement.config(text="        ↳ " + lbl_label_placement_txt[lang])
    rad_label_placement_move.config(text=["Copy", "Copiar"][lang])
    rad_label_placement_copy.config(text=["Move", "Mover"][lang])
    lbl_csv.config(text=lbl_csv_txt[lang])
    lbl_thresh.config(text=lbl_thresh_txt[lang])
    btn_start_postprocess.config(text=btn_start_postprocess_txt[lang])
    
    # update texts of train tab
    req_params.config(text=" " + req_params_txt[lang] + " ")
    lbl_train_type.config(text=lbl_train_type_txt[lang])
    update_dpd_options(dpd_train_type, req_params, var_train_type, dpd_train_type_options, toggle_train_type, row_train_type, lbl_train_type, from_lang)
    lbl_annotated_data.config(text=lbl_annotated_data_txt[lang])
    btn_annotated_data.config(text=browse_txt[lang])
    lbl_learning_model.config(text=lbl_learning_model_txt[lang])
    update_dpd_options(dpd_learning_model, req_params, var_learning_model, dpd_learning_model_options, set_learning_model, row_learning_model, lbl_learning_model, from_lang)
    lbl_model_architecture.config(text=lbl_model_architecture_txt[lang])
    update_dpd_options(dpd_model_architecture, req_params, var_model_architecture, dpd_model_architecture_options, set_model_architecture, row_model_architecture, lbl_model_architecture, from_lang)
    lbl_n_epochs.config(text=lbl_n_epochs_txt[lang])
    update_ent_text(ent_n_epochs, f"{eg_txt[lang]}: 300")
    lbl_results_dir.config(text=lbl_results_dir_txt[lang])
    btn_results_dir.config(text=browse_txt[lang])
    lbl_resume_checkpoint.config(text=lbl_resume_checkpoint_txt[lang])
    btn_resume_checkpoint.config(text=browse_txt[lang])
    lbl_project_name.config(text=lbl_project_name_txt[lang])
    update_ent_text(ent_project_name, f"{eg_txt[lang]}: {['Tiger ID', 'Proyecto A'][lang]}")
    adv_params.config(text=" " + adv_params_txt[lang] + " ")
    lbl_val_prop.config(text=lbl_val_prop_txt[lang])
    lbl_test_prop.config(text=lbl_test_prop_txt[lang])
    lbl_train_gpu.config(text=lbl_train_gpu_txt[lang])
    lbl_batch_size.config(text=f"{lbl_batch_size_txt[lang]} {lbl_batch_size_txt_extra[lang]}")
    update_ent_text(ent_batch_size, f"{eg_txt[lang]}: 8")
    lbl_n_workers.config(text=f"{lbl_n_workers_txt[lang]} {lbl_n_workers_txt_extra[lang]}")
    update_ent_text(ent_n_workers, f"{eg_txt[lang]}: 2")
    lbl_image_size_for_training.config(text=f"{lbl_image_size_for_training_txt[lang]} {lbl_image_size_for_training_txt_extra[lang]}")
    update_ent_text(ent_image_size_for_training, f"{eg_txt[lang]}: 1280")
    lbl_cache_imgs.config(text=lbl_cache_imgs_txt[lang])
    lbl_hyper_file.config(text=lbl_hyper_file_txt[lang])
    update_dpd_options(dpd_hyper_file, adv_params, var_hyper_file, dpd_hyper_file_options, set_hyper_file, row_hyper_file, lbl_hyper_file, from_lang)
    lbl_evolve.config(text=lbl_evolve_txt[lang])
    lbl_n_generations.config(text=f"{lbl_n_generations_txt[lang]} {lbl_n_generations_txt_extra[lang]}")
    update_ent_text(ent_n_generations, f"{eg_txt[lang]}: 500")
    lbl_run_name.config(text=f"{lbl_run_name_txt[lang]} {lbl_run_name_txt_extra[lang]}")
    update_ent_text(ent_run_name, f"{eg_txt[lang]}: {['Initial run', 'Proceso inicial'][lang]}")
    lbl_n_freeze_layers.config(text=f"{lbl_n_freeze_layers_txt[lang]} {lbl_n_freeze_layers_txt_extra[lang]}")
    update_ent_text(ent_n_freeze_layers, f"{eg_txt[lang]}: 12")
    btn_start_training.config(text=btn_start_training_txt[lang])
    train_output.config(text=" " + train_output_txt[lang] + " ")
    btn_cancel_training.config(text=btn_cancel_training_txt[lang])

    # update texts of annotate tab
    annotate_text.config(state=NORMAL)
    annotate_text.delete('1.0', END)
    write_annotate_tab()
    annot_frame.config(text=annot_frame_txt[lang])
    lbl_annot_dir.config(text=lbl_annot_dir_txt[lang])
    btn_annot_dir.config(text=browse_txt[lang])
    lbl_annot_classes.config(text=lbl_annot_classes_txt[lang])
    update_ent_text(ent_annot_classes, f"{eg_txt[lang]}: {example_classes[lang]}")
    btn_start_annot.config(text=btn_start_annot_txt[lang])

    # update texts of help tab
    help_text.config(state=NORMAL)
    help_text.delete('1.0', END)
    write_help_tab()

    # update texts of about tab
    about_text.config(state=NORMAL)
    about_text.delete('1.0', END)
    write_about_tab()

# update frame states
def update_frame_states():
    # check dir validity
    if var_choose_folder.get() not in ["", "/", "\\", ".", "~", ":"] and os.path.isdir(var_choose_folder.get()):
        complete_frame(fst_step)
    else:
        enable_frame(fst_step)

    # check json files
    img_json = False
    if os.path.isfile(os.path.join(var_choose_folder.get(), "image_recognition_file.json")):
        img_json = True
    vid_json = False
    if os.path.isfile(os.path.join(var_choose_folder.get(), "video_recognition_file.json")):
        vid_json = True
    
    # check if dir is already processed
    if img_json or vid_json:
        complete_frame(snd_step)
        enable_frame(trd_step)
    else:
        enable_frame(snd_step)
        disable_frame(trd_step)

# show entry box if classes.txt is not yet present
def grid_annot_classes():
    classes_txt = os.path.join(var_annot_dir.get(), "classes.txt")
    if not os.path.isfile(classes_txt):
        lbl_annot_classes.grid(row=row_annot_classes, sticky='nesw')
        ent_annot_classes.grid(row=row_annot_classes, column=1, sticky='nesw', padx=5)
    else:
        lbl_annot_classes.grid_remove()
        ent_annot_classes.grid_remove()

# set hyperparameter file variable based on user selection
def set_hyper_file(self):
    # log
    print(f"EXECUTED: {sys._getframe().f_code.co_name}({locals()})\n")

    # if "other" is selected
    if self == dpd_hyper_file_options[lang][6]:
        browse_file(var_hyper_file,
                    var_hyper_file_short,
                    var_hyper_file_path,
                    dsp_hyper_file,
                    [("YAML file","*.yaml")],
                    20,
                    dpd_hyper_file_options[lang],
                    row_hyper_file)
    
    # if one of the pre-defined files is selected
    else:
        yolo_hyps = os.path.join(EcoAssist_files, "yolov5", "data", "hyps")
        if self == dpd_hyper_file_options[lang][0]:
            var_hyper_file_path.set("")
        elif self == dpd_hyper_file_options[lang][1]:
            var_hyper_file_path.set(os.path.join(yolo_hyps, "hyp.scratch-low.yaml"))
        elif self == dpd_hyper_file_options[lang][2]:
            var_hyper_file_path.set(os.path.join(yolo_hyps, "hyp.scratch-med.yaml"))
        elif self == dpd_hyper_file_options[lang][3]:
            var_hyper_file_path.set(os.path.join(yolo_hyps, "hyp.scratch-high.yaml"))
        elif self == dpd_hyper_file_options[lang][4]:
            var_hyper_file_path.set(os.path.join(yolo_hyps, "hyp.Objects365.yaml"))
        elif self == dpd_hyper_file_options[lang][5]:
            var_hyper_file_path.set(os.path.join(yolo_hyps, "hyp.VOC.yaml"))

# set model architecture variable based on user selection
def set_model_architecture(self):
    # log
    print(f"EXECUTED: {sys._getframe().f_code.co_name}({locals()})\n")

    # if "other config" is selected
    if self == dpd_model_architecture_options[lang][5]:
        browse_file(var_model_architecture,
                    var_model_architecture_short,
                    var_model_architecture_path,
                    dsp_model_architecture,
                    [("YAML file","*.yaml")],
                    20,
                    dpd_model_architecture_options[lang],
                    row_model_architecture)
    
    # if one of the pre-defined archs is selected
    else:
        model_architectures = os.path.join(EcoAssist_files, "yolov5", "models")
        if self == dpd_model_architecture_options[lang][0]:
            var_model_architecture_path.set(os.path.join(model_architectures, "yolov5n.yaml"))
        elif self == dpd_model_architecture_options[lang][1]:
            var_model_architecture_path.set(os.path.join(model_architectures, "yolov5s.yaml"))
        elif self == dpd_model_architecture_options[lang][2]:
            var_model_architecture_path.set(os.path.join(model_architectures, "yolov5m.yaml"))
        elif self == dpd_model_architecture_options[lang][3]:
            var_model_architecture_path.set(os.path.join(model_architectures, "yolov5l.yaml"))
        elif self == dpd_model_architecture_options[lang][4]:
            var_model_architecture_path.set(os.path.join(model_architectures, "yolov5x.yaml"))
        elif self == dpd_model_architecture_options[lang][6]:
            var_model_architecture_path.set("")

# set learning model variable based on user selection
def set_learning_model(self):
    # log
    print(f"EXECUTED: {sys._getframe().f_code.co_name}({locals()})\n")

    # set variable
    choice = var_learning_model.get()

    # user selected custom model
    if choice == dpd_learning_model_options[lang][7]:
        # choose file
        browse_file(var_learning_model,
                    var_learning_model_short,
                    var_learning_model_path,
                    dsp_learning_model,
                    [("Yolov5 model","*.pt")],
                    20,
                    dpd_learning_model_options[lang],
                    row_learning_model)

        # add widget to freeze layers if custom model is selected
        if not var_learning_model_path.get().startswith(os.path.join(EcoAssist_files, "pretrained_models")):
            lbl_n_freeze_layers.grid(row=row_n_freeze_layers, sticky='nesw')
            ent_n_freeze_layers.grid(row=row_n_freeze_layers, column=1, sticky='nesw', padx=5)
    
    # user selected pre-defined model or from scratch
    else:
        var_learning_model_short.set("")
        lbl_n_freeze_layers.grid_forget()
        ent_n_freeze_layers.grid_forget()

    # show scratch learning widgets
    if choice == dpd_learning_model_options[lang][8]:
        lbl_model_architecture.grid(row=row_model_architecture, sticky='nesw', pady=2)
        dpd_model_architecture = OptionMenu(req_params, var_model_architecture, *dpd_model_architecture_options[lang], command=set_model_architecture)  # recreate dpd with translated options
        dpd_model_architecture.grid(row=row_model_architecture, column=1, sticky='nesw', padx=5)
        dpd_model_architecture.configure(width=1)
 
    # hide scratch learning widgets
    else:
        remove_widgets_based_on_location(master = req_params,
                                         rows = [row_model_architecture],
                                         cols = [0, 1])
    
    # set path to model
    pretrained_models = os.path.join(EcoAssist_files, "pretrained_models")
    if choice == dpd_learning_model_options[lang][0]:
        var_learning_model_path.set(os.path.join(pretrained_models, "md_v5a.0.0.pt"))
    elif choice == dpd_learning_model_options[lang][1]:
        var_learning_model_path.set(os.path.join(pretrained_models, "md_v5b.0.0.pt"))
    elif choice == dpd_learning_model_options[lang][2]:
        var_learning_model_path.set(os.path.join(pretrained_models, "yolov5n.pt"))
    elif choice == dpd_learning_model_options[lang][3]:
        var_learning_model_path.set(os.path.join(pretrained_models, "yolov5s.pt"))
    elif choice == dpd_learning_model_options[lang][4]:
        var_learning_model_path.set(os.path.join(pretrained_models, "yolov5m.pt"))
    elif choice == dpd_learning_model_options[lang][5]:
        var_learning_model_path.set(os.path.join(pretrained_models, "yolov5l.pt"))
    elif choice == dpd_learning_model_options[lang][6]:
        var_learning_model_path.set(os.path.join(pretrained_models, "yolov5x.pt"))
    elif choice == dpd_learning_model_options[lang][8]:
        var_learning_model_path.set("")

# set global cancel var to end training
def cancel_training():
    cancel_training_bool.set(True)

# check if user entered text in entry widget
def no_user_input(var):
    if var.get() == "" or var.get().startswith("E.g.:") or var.get().startswith("Ejem.:"):
        return True
    else:
        return False

# send text to output window and log 
def send_to_output_window(txt):
    # show user
    txt_train_output.configure(state=NORMAL)
    txt_train_output.insert(END, f"{txt}\n")
    txt_train_output.see("end")
    txt_train_output.configure(state=DISABLED)

    # log
    print(txt)

# show warning if not valid input
def invalid_value_warning(str, numeric = True):
    string = [f"You either entered an invalid value for the {str}, or none at all.", f"Ingresó un valor no válido para {str} o ninguno."][lang] 
    if numeric:
        string += [" You can only enter numberic characters.", " Solo puede ingresar caracteres numéricos."][lang]
    mb.showerror(invalid_value_txt[lang], string)

# disable widgets based on row and col indeces
def disable_widgets_based_on_location(master, rows, cols):
    # list widgets to be removed
    widgets = []
    for row in rows:
        for col in cols:
            l = master.grid_slaves(row, col)
            for i in l:
                widgets.append(i)

    # remove widgets
    for widget in widgets:
        widget.config(state=DISABLED)

# remove widgets based on row and col indexes
def remove_widgets_based_on_location(master, rows, cols):
    # list widgets to be removed
    widgets = []
    for row in rows:
        for col in cols:
            l = master.grid_slaves(row, col)
            for i in l:
                widgets.append(i)

    # remove widgets
    for widget in widgets:
        widget.grid_forget()

# show and hide project widget depending on existing projects and user input
def grid_project_name():
    # set vars
    global var_project_name
    global ent_project_name
    global lbl_project_name
    global lbl_project_name_txt

    # remove all project name widgets
    remove_widgets_based_on_location(master = req_params,
                                     rows = [row_project_name],
                                     cols = [0, 1])

    # check dir validity
    if var_results_dir.get() in ["", "/", "\\", ".", "~", ":"] or not os.path.isdir(var_results_dir.get()):
        req_params.grid_rowconfigure(row_project_name, minsize=0)
        return
    
    # set min row size
    req_params.grid_rowconfigure(row_project_name, minsize=minsize_rows)

    # check if any existing projects
    dpd_project_name_options = sorted([o for o in os.listdir(var_results_dir.get()) if os.path.isdir(os.path.join(var_results_dir.get(), o))])

    # shared label widget
    lbl_project_name_txt = ["Project name", "Nombre del proyecto"]
    lbl_project_name = tk.Label(req_params, text=lbl_project_name_txt[lang], pady=2, width=1, anchor="w")
    lbl_project_name.grid(row=row_project_name, sticky='nesw')

    # if existing projects: dropdown menu
    if len(dpd_project_name_options) != 0:
        dpd_project_name_options.append(new_project_txt[lang])
        dpd_project_name = OptionMenu(req_params, var_project_name, *dpd_project_name_options, command=swtich_dropdown_to_entry)
        dpd_project_name.configure(width=1)
        dpd_project_name.grid(row=row_project_name, column=1, sticky='nesw', padx=5)
        var_project_name.set(dpd_project_name_options[0])

    # if no existing projects: entry box
    else:
        ent_project_name.grid(row=row_project_name, column=1, sticky='nesw', padx=5)
        var_project_name.set("")

        # first time user will see this entry box
        if ent_project_name.cget("fg") == "grey":
            ent_project_name.insert(0, f"{eg_txt[lang]}: {['Tiger ID', 'Proyecto A'][lang]}")
            ent_project_name.bind("<FocusIn>", project_name_focus_in)

# show entry box when user selected to add a new project from dropdown menu
def swtich_dropdown_to_entry(self):
    # set vars
    global var_project_name
    global ent_project_name

    # remove all project name widgets
    if self in new_project_txt: # new project
        project_name_widgets = [*req_params.grid_slaves(row_project_name, 0), *req_params.grid_slaves(row_project_name, 1)]
        for widget in project_name_widgets:
            widget.grid_forget()

        # add entry widget, label and button
        lbl_project_name_txt = ["Project name", "Nombre del proyecto"]
        lbl_project_name = tk.Label(req_params, text=lbl_project_name_txt[lang], pady=2, width=1, anchor="w")
        lbl_project_name.grid(row=row_project_name, sticky='nesw')
        var_project_name.set("")
        ent_project_name.grid(row=row_project_name, column=1, sticky='nesw', padx=5)
        ent_project_name.configure(fg="black")
        btn_project_name = Button(req_params, text="x", command=grid_project_name)
        btn_project_name.grid(row=row_project_name, column=0, sticky='e', padx=5)

# create hyperlinks (thanks marvin from GitHub) 
class HyperlinkManager:
    def __init__(self, text):
        self.text = text
        self.text.tag_config("hyper", foreground="blue", underline=1)
        self.text.tag_bind("hyper", "<Enter>", self._enter)
        self.text.tag_bind("hyper", "<Leave>", self._leave)
        self.text.tag_bind("hyper", "<Button-1>", self._click)
        self.reset()

    def reset(self):
        self.links = {}

    def add(self, action):
        tag = "hyper-%d" % len(self.links)
        self.links[tag] = action
        return "hyper", tag

    def _enter(self, event):
        self.text.config(cursor="hand2")

    def _leave(self, event):
        self.text.config(cursor="")

    def _click(self, event):
        for tag in self.text.tag_names(CURRENT):
            if tag[:6] == "hyper-":
                self.links[tag]()
                return

# set cancel variable to true
def cancel():
    # log
    print(f"EXECUTED: {sys._getframe().f_code.co_name}({locals()})\n")
    
    global cancel_var
    cancel_var = True

# set all children of frame to disabled state
def disable_widgets(frame):
    children = frame.winfo_children()
    for child in children:
        # labelframes have no state
        if child.winfo_class() != "Labelframe":
            child.config(state=DISABLED)

# set all children of frame to normal state
def enable_widgets(frame):
    children = frame.winfo_children()
    for child in children:
        # labelframes have no state
        if child.winfo_class() != "Labelframe":
            child.config(state=NORMAL)

# toggle options to resume from existing training
def toggle_train_type(self):
    # log
    print(f"EXECUTED: {sys._getframe().f_code.co_name}({locals()})\n")

    # change settings
    if self == dpd_train_type_options[lang][0]:
        # start new training
        for child in req_params.winfo_children():
            child.config(state=NORMAL)
        for child in adv_params.winfo_children():
            child.config(state=NORMAL)
        lbl_resume_checkpoint.grid_forget()
        btn_resume_checkpoint.grid_forget()
        dsp_resume_checkpoint.grid_forget()
    elif self == dpd_train_type_options[lang][1]:
        # resume existing training
        disable_widgets_based_on_location(req_params,
                                          rows = [1, 2, 3, 4, 5, 7],
                                          cols = [0, 1])
        disable_widgets(adv_params)
        lbl_resume_checkpoint.grid(row=row_resume_checkpoint, sticky='nesw', pady=2)
        lbl_resume_checkpoint.config(state=NORMAL)
        btn_resume_checkpoint.grid(row=row_resume_checkpoint, column=1, sticky='nesw', padx=5)
        btn_resume_checkpoint.config(state=NORMAL)
        dsp_resume_checkpoint.config(state=NORMAL)
        var_resume_checkpoint_path.set("")

# show warning and toggle model threshold option
md_thresh_warning = True
def toggle_md_thresh():
    global md_thresh_warning
    if var_excl_detecs.get() and not md_thresh_warning:
        place_md_thresh()
    elif var_excl_detecs.get() and md_thresh_warning:
        md_thresh_warning = False
        if mb.askyesno(warning_txt[lang], ["It is strongly advised to not exclude detections from the model output file. "
                       "Only set the confidence threshold to a very small value if you really know what you're doing. "
                       "The model output should include just about everything that the model produces. If you,"
                       " because for some reason, want an extra-small output file, you would typically use a threshold of"
                       " 0.01 or 0.05.\n\nIf you want to use a threshold for post-processing features (visualization / "
                       "folder separation / cropping / annotation), please use the associated thresholds there.\n\nDo "
                       "you still want to exclude detections from the model output file?",
                       "Se recomienda encarecidamente no excluir las detecciones del fichero de salida del modelo. Sólo"
                       " ajuste el umbral de confianza a un valor muy pequeño si realmente sabe lo que está haciendo. La"
                       " salida del modelo debería incluir casi todo lo que el modelo produce. Si usted, por alguna razón,"
                       " quiere un archivo de salida muy pequeño, debería usar un umbral de 0.01 o 0.05.\n\nSi desea utilizar"
                       " un umbral para las características de post-procesamiento (visualización / separación de carpetas "
                       "/ recorte / anotación), por favor, utilice los umbrales asociados allí.\n\n¿Sigue queriendo excluir "
                       "las detecciones del archivo de salida del modelo?"][lang]):
            place_md_thresh()
        else:
            var_excl_detecs.set(False)
            remove_md_thresh()
    else:
        remove_md_thresh()

# show warning for absolute paths option
shown_abs_paths_warning = True
def abs_paths_warning():
    global shown_abs_paths_warning
    if var_abs_paths.get() and shown_abs_paths_warning:
        mb.showinfo(warning_txt[lang], ["It is not recommended to use absolute paths in the output file. Third party software (such "
                    "as Timelapse, Agouti etc.) will not be able to read the json file if the paths are absolute. Only enable"
                    " this option if you know what you are doing.",
                    "No se recomienda utilizar rutas absolutas en el archivo de salida. Software de terceros (como Timelapse, "
                    "Agouti etc.) no podrán leer el archivo json si las rutas son absolutas. Sólo active esta opción si sabe lo"
                    " que está haciendo."][lang])
        shown_abs_paths_warning = False

# place model threshold
def place_md_thresh():    
    lbl_md_thresh.grid(row=row_md_thresh, sticky='nesw', pady=2)
    scl_md_thresh.grid(row=row_md_thresh, column=1, sticky='ew', padx=10)
    dsp_md_thresh.grid(row=row_md_thresh, column=0, sticky='e', padx=0)

# remove model threshold
def remove_md_thresh():
    lbl_md_thresh.grid_remove()
    scl_md_thresh.grid_remove()
    dsp_md_thresh.grid_remove()

# toggle image size entry box
def toggle_image_size_for_deploy():
    if var_use_custom_img_size_for_deploy.get():
        lbl_image_size_for_deploy.grid(row=row_image_size_for_deploy, sticky='nesw', pady=2)
        ent_image_size_for_deploy.grid(row=row_image_size_for_deploy, column=1, sticky='nesw', padx=5)
    else:
        lbl_image_size_for_deploy.grid_remove()
        ent_image_size_for_deploy.grid_remove()

# toggle separation subframe
def toggle_sep_frame():
    if var_separate_files.get():
        enable_widgets(sep_frame)
        sep_frame.configure(fg='black')
    else:
        disable_widgets(sep_frame)
        sep_frame.configure(fg='grey80')

# toggle annotation creation subframe
def toggle_annot_create_frame():
    if var_yol_files.get():
        enable_widgets(annot_create_frame)
        annot_create_frame.configure(fg='black')
        toggle_label_placement()
    else:
        disable_widgets(annot_create_frame)
        annot_create_frame.configure(fg='grey80')

# toggle image subframe
def toggle_img_frame():
    if var_process_img.get():
        enable_widgets(img_frame)
        toggle_checkpoint_freq()
        img_frame.configure(fg='black')
    else:
        disable_widgets(img_frame)
        img_frame.configure(fg='grey80')

# toggle video subframe
def toggle_vid_frame():
    if var_process_vid.get():
        enable_widgets(vid_frame)
        toggle_nth_frame()
        vid_frame.configure(fg='black')
    else:
        disable_widgets(vid_frame)
        vid_frame.configure(fg='grey80')

# convert frame to completed
def complete_frame(frame):
    global check_mark_one_row
    global check_mark_two_rows
    # adjust frames
    frame.configure(relief = 'groove')
    if frame.cget('text').startswith(f' {step_txt[lang]}'):
        # all step frames
        frame.configure(fg='green3')
    if frame.cget('text').startswith(f' {step_txt[lang]} 2'):
        # snd_step
        img_frame.configure(relief = 'groove')
        vid_frame.configure(relief = 'groove')
    if frame.cget('text').startswith(f' {step_txt[lang]} 1'):
        # fst_step
        dsp_choose_folder.config(image=check_mark_one_row, compound='left')
        btn_choose_folder.config(text=f"{change_folder_txt[lang]}?")
    else:
        # the rest
        if not frame.cget('text').startswith(f' {step_txt[lang]}'):
            # sub frames of trd_step only
            frame.configure(fg='green3')
        # add check mark
        lbl_check_mark = Label(frame, image=check_mark_two_rows)
        lbl_check_mark.image = check_mark_two_rows
        lbl_check_mark.grid(row=0, column=0, rowspan=15, columnspan=2, sticky='nesw')
        # add buttons
        btn_view_results = Button(master=frame, text=view_results_txt[lang], height=1, width=10, command=lambda: view_results(frame))
        btn_view_results.grid(row=0, column=1, sticky='e')
        btn_uncomplete = Button(master=frame, text=again_txt[lang], height=1, width=10, command=lambda: enable_frame(frame))
        btn_uncomplete.grid(row=1, column=1, sticky='e')

# enable a frame
def enable_frame(frame):
    uncomplete_frame(frame)
    enable_widgets(frame)
    # all frames
    frame.configure(relief = 'solid')
    if frame.cget('text').startswith(f' {step_txt[lang]}'):
        # fst_step, snd_step and trd_step
        frame.configure(fg='darkblue')
    if frame.cget('text').startswith(f' {step_txt[lang]} 2'):
        # snd_step only
        toggle_img_frame()
        img_frame.configure(relief = 'solid')
        toggle_vid_frame()
        vid_frame.configure(relief = 'solid')
    if frame.cget('text').startswith(f' {step_txt[lang]} 3'):
        # trd_step only
        toggle_sep_frame()
        sep_frame.configure(relief = 'solid')
        toggle_annot_create_frame()
        annot_create_frame.configure(relief = 'solid')

# remove checkmarks and complete buttons
def uncomplete_frame(frame):
    if not frame.cget('text').startswith(f' {step_txt[lang]}'):
        # subframes in trd_step only
        frame.configure(fg='black')
    if not frame.cget('text').startswith(f' {step_txt[lang]} 1'):
        # all except step 1
        children = frame.winfo_children()
        for child in children:
            if child.winfo_class() == "Button" or child.winfo_class() == "Label":
                if child.cget('text') == again_txt[lang] or child.cget('text') == view_results_txt[lang] or child.cget('image') != "":
                    child.grid_remove()

# disable a frame
def disable_frame(frame):
    uncomplete_frame(frame)
    disable_widgets(frame)
    # all frames
    frame.configure(fg='grey80')
    frame.configure(relief = 'flat')
    if frame.cget('text').startswith(f' {step_txt[lang]} 2'):
        # snd_step only
        disable_widgets(img_frame)
        img_frame.configure(fg='grey80')
        img_frame.configure(relief = 'flat')
        disable_widgets(vid_frame)
        vid_frame.configure(fg='grey80')
        vid_frame.configure(relief = 'flat')
    if frame.cget('text').startswith(f' {step_txt[lang]} 3'):
        # trd_step only
        disable_widgets(sep_frame)
        sep_frame.configure(fg='grey80')
        sep_frame.configure(relief = 'flat')
        disable_widgets(annot_create_frame)
        annot_create_frame.configure(fg='grey80')
        annot_create_frame.configure(relief = 'flat')
    
# check if checkpoint is present and set checkbox accordingly
def disable_chb_cont_checkpnt():
    if var_cont_checkpnt.get():
        var_cont_checkpnt.set(check_checkpnt())

# set minimum row size for all rows in a frame
def set_minsize_rows(frame):
    row_count = frame.grid_size()[1]
    for row in range(row_count):
        frame.grid_rowconfigure(row, minsize=minsize_rows)

# toggle state of checkpoint frequency
def toggle_checkpoint_freq():
    if var_use_checkpnts.get():
        lbl_checkpoint_freq.config(state=NORMAL)
        ent_checkpoint_freq.config(state=NORMAL)
    else:
        lbl_checkpoint_freq.config(state=DISABLED)
        ent_checkpoint_freq.config(state=DISABLED)

# toggle state of label placement method
def toggle_label_placement():
    if var_uniquify.get():
        lbl_label_placement.config(state=NORMAL)
        rad_label_placement_move.config(state=NORMAL)
        rad_label_placement_copy.config(state=NORMAL)
    else:
        lbl_label_placement.config(state=DISABLED)
        rad_label_placement_move.config(state=DISABLED)
        rad_label_placement_copy.config(state=DISABLED)

# toggle state of nth frame
def toggle_nth_frame():
    if var_not_all_frames.get():
        lbl_nth_frame.config(state=NORMAL)
        ent_nth_frame.config(state=NORMAL)
    else:
        lbl_nth_frame.config(state=DISABLED)
        ent_nth_frame.config(state=DISABLED)

# toggle hyperparameter evolution
def toggle_n_evolutions():
    mb.showwarning(warning_txt[lang], ["Note that evolution is generally expensive and time consuming, as the base scenario is trained hundreds of times."
                              " Be aware that it can take weeks or months to finish.",
                              "Tenga en cuenta que la evolución es generalmente costosa y requiere mucho tiempo, ya que el escenario base se entrena "
                              "cientos de veces. Tenga en cuenta que puede tardar semanas o meses en terminarse."][lang])
    if var_evolve.get():
        lbl_n_generations.grid(row=row_n_generations, sticky='nesw')
        ent_n_generations.grid(row=row_n_generations, column=1, sticky='nesw', padx=5)
        adv_params.grid_rowconfigure(row_n_generations, minsize=minsize_rows)
    else:
        lbl_n_generations.grid_forget()
        ent_n_generations.grid_forget()
        adv_params.grid_rowconfigure(row_n_generations, minsize=0)

# functions to delete the grey text in the entry boxes for the...
# ... image size fro deploy
image_size_for_deploy_init = True
def image_size_for_deploy_focus_in(_):
    global image_size_for_deploy_init
    if image_size_for_deploy_init:
        ent_image_size_for_deploy.delete(0, tk.END)
        ent_image_size_for_deploy.config(fg='black')
    image_size_for_deploy_init = False

# ... checkpoint frequency
checkpoint_freq_init = True
def checkpoint_freq_focus_in(_):
    global checkpoint_freq_init
    if checkpoint_freq_init:
        ent_checkpoint_freq.delete(0, tk.END)
        ent_checkpoint_freq.config(fg='black')
    checkpoint_freq_init = False

# ... nth frame
nth_frame_init = True
def nth_frame_focus_in(_):
    global nth_frame_init
    if nth_frame_init:
        ent_nth_frame.delete(0, tk.END)
        ent_nth_frame.config(fg='black')
    nth_frame_init = False

# ... project name
project_name_init = True
def project_name_focus_in(_):
    global project_name_init
    if project_name_init:
        ent_project_name.delete(0, tk.END)
        ent_project_name.config(fg='black')
    project_name_init = False

# ... run name
run_name_init = True
def run_name_focus_in(_):
    global run_name_init
    if run_name_init:
        ent_run_name.delete(0, tk.END)
        ent_run_name.config(fg='black')
    run_name_init = False

# ... number of epochs
n_epochs_init = True
def n_epochs_focus_in(_):
    global n_epochs_init
    if n_epochs_init:
        ent_n_epochs.delete(0, tk.END)
        ent_n_epochs.config(fg='black')
    n_epochs_init = False

# ... number of layers to freeze
n_freeze_layers_init = True
def n_freeze_layers_focus_in(_):
    global n_freeze_layers_init
    if n_freeze_layers_init:
        ent_n_freeze_layers.delete(0, tk.END)
        ent_n_freeze_layers.config(fg='black')
    n_freeze_layers_init = False

# ... batch size
batch_size_init = True
def batch_size_focus_in(_):
    global batch_size_init
    if batch_size_init:
        ent_batch_size.delete(0, tk.END)
        ent_batch_size.config(fg='black')
    batch_size_init = False

# ... number of generations
n_generations_init = True
def n_generations_focus_in(_):
    global n_generations_init
    if n_generations_init:
        ent_n_generations.delete(0, tk.END)
        ent_n_generations.config(fg='black')
    n_generations_init = False

# ... image size
image_size_for_training_init = True
def image_size_for_training_focus_in(_):
    global image_size_for_training_init
    if image_size_for_training_init:
        ent_image_size_for_training.delete(0, tk.END)
        ent_image_size_for_training.config(fg='black')
    image_size_for_training_init = False

# ... annotation classes
annot_classes_init = True
def annot_classes_focus_in(_):
    global annot_classes_init
    if annot_classes_init:
        ent_annot_classes.delete(0, tk.END)
        ent_annot_classes.config(fg='black')
    annot_classes_init = False
    
# ... n dataloader workers
n_workers_init = True
def n_workers_focus_in(_):
    global n_workers_init
    if n_workers_init:
        ent_n_workers.delete(0, tk.END)
        ent_n_workers.config(fg='black')
    n_workers_init = False

##########################################
############# TKINTER WINDOW #############
##########################################

# make it look similar on different systems
if os.name == "nt": # windows
    text_font = "TkDefaultFont"
    resize_img_factor = 0.95
    text_size_adjustment_factor = 0.83
    first_level_frame_font_size = 13
    second_level_frame_font_size = 11
    label_width = 320
    widget_width = 150
    frame_width = label_width + widget_width + 50
    minsize_rows = 28
elif sys.platform == "linux" or sys.platform == "linux2": # linux
    text_font = "Times"
    resize_img_factor = 1
    text_size_adjustment_factor = 0.7
    first_level_frame_font_size = 15
    second_level_frame_font_size = 13
    label_width = 330
    widget_width = 160
    frame_width = label_width + widget_width + 50
    minsize_rows = 28
else: # macOS
    text_font = "TkDefaultFont"
    resize_img_factor = 1
    text_size_adjustment_factor = 1
    first_level_frame_font_size = 15
    second_level_frame_font_size = 13
    label_width = 320
    widget_width = 150
    frame_width = label_width + widget_width + 50
    minsize_rows = 28

# tkinter main window
root = Tk()
root.title(f"EcoAssist v{version}")
root.geometry()
root.configure(background="white")
tabControl = ttk.Notebook(root)

# prepare logo
logo_path = os.path.join(EcoAssist_files,'EcoAssist', 'imgs', 'logo.png')
logo = Image.open(logo_path)
white_bg_logo = Image.new("RGBA", logo.size, "WHITE")
white_bg_logo.paste(logo, (0, 0), logo)
white_bg_logo.convert('RGB')
white_bg_logo = ImageTk.PhotoImage(white_bg_logo)
grey_bg_logo = ImageTk.PhotoImage(logo)

# prepare fox image
fox = Image.open(os.path.join(EcoAssist_files, 'EcoAssist', 'imgs', 'mari.jpeg'))
full_width, full_height = fox.size
chosen_width = full_width 
chosen_height = full_width * 0.4
top = 130
bottom = top + chosen_height
left = 0
right = chosen_width
fox = fox.crop((left, top, right, bottom))
fox = fox.resize((int(resize_img_factor * 422), 150), Image.Resampling.LANCZOS)
rad = 10
back = Image.new('RGB', (fox.size[0] + rad, fox.size[1]), (255, 255, 255))
back.paste(fox, (0, 0))
mask = Image.new('L', (fox.size[0] + rad, fox.size[1]), 255)
blck = Image.new('L', (fox.size[0] - rad, fox.size[1]), 0)
mask.paste(blck, (0, 0))
blur = back.filter(ImageFilter.GaussianBlur(rad / 2))
back.paste(blur, mask=mask)
fox = ImageTk.PhotoImage(back)

# prepare ocelot image
ocelot = Image.open(os.path.join(EcoAssist_files, 'EcoAssist', 'imgs', 'geovani.jpeg'))
full_width, full_height = ocelot.size
chosen_width = full_width
chosen_height = full_width * 0.47
top = 650
bottom = top + chosen_height
left = 0
right = chosen_width
ocelot = ocelot.crop((left, top, right, bottom))
ocelot = ocelot.resize((int(resize_img_factor * 422), 150), Image.Resampling.LANCZOS) 
back = Image.new('RGB', (ocelot.size[0], ocelot.size[1]), (255, 255, 255))
back.paste(ocelot, (rad, 0))
mask = Image.new('L', (ocelot.size[0], ocelot.size[1]), 255)
blck = Image.new('L', (ocelot.size[0], ocelot.size[1]), 0)
mask.paste(blck, (2 * rad, 0))
blur = back.filter(ImageFilter.GaussianBlur(rad / 2))
back.paste(blur, mask=mask)
ocelot = ImageTk.PhotoImage(back)

# print the images on the tkinter window
logo_widget = tk.Label(root, image=white_bg_logo, bg="white", highlightthickness=0, highlightbackground="white")
fox_widget = tk.Label(root, image=fox, bg="white", highlightthickness=0, highlightbackground="white")
ocelot_widget = tk.Label(root, image=ocelot, bg="white", highlightthickness=0, highlightbackground="white")
logo_widget.grid(column=0, row=0, sticky='ns', pady=(3, 0), padx=(0, 0))
fox_widget.grid(column=0, row=0, sticky='wns', pady=(3, 0), padx=(3, 0))
ocelot_widget.grid(column=0, row=0, sticky='ens', pady=(3, 0), padx=(0, 3))

# prepare check mark for later use
check_mark = Image.open(os.path.join(EcoAssist_files, 'EcoAssist', 'imgs', 'check_mark.png'))
check_mark_one_row = check_mark.resize((22, 22), Image.Resampling.LANCZOS)
check_mark_one_row = ImageTk.PhotoImage(check_mark_one_row)
check_mark_two_rows = check_mark.resize((45, 45), Image.Resampling.LANCZOS)
check_mark_two_rows = ImageTk.PhotoImage(check_mark_two_rows)


# link to tutorial

# deploy tab
deploy_tab = ttk.Frame(tabControl)
deploy_tab.columnconfigure(0, weight=1, minsize=frame_width)
deploy_tab.columnconfigure(1, weight=1, minsize=frame_width)
deploy_tab_text = ['Deploy', 'Despliegue']
tabControl.add(deploy_tab, text=deploy_tab_text[lang])


# grid
tabControl.grid()

#### deploy tab
### first step
fst_step_txt = ['Passo 1: Escolher pasta para ser analizada', 'Paso 1: Elige Carpeta para analizar']
row_fst_step = 1
fst_step = LabelFrame(deploy_tab, text=" " + fst_step_txt[lang] + " ", pady=2, padx=5, relief='solid', highlightthickness=5, font=100, fg='darkblue', borderwidth=2)
fst_step.configure(font=(text_font, first_level_frame_font_size, "bold"))
fst_step.grid(column=0, row=row_fst_step, columnspan=2, sticky='ew')

# choose folder
row_choose_folder = 0
var_choose_folder = StringVar()
var_choose_folder_short = StringVar()
dsp_choose_folder = Label(master=fst_step, textvariable=var_choose_folder_short)
btn_choose_folder = Button(master=fst_step, text=browse_txt[lang], command=lambda: [browse_dir(var_choose_folder, var_choose_folder_short, dsp_choose_folder, 100, row_choose_folder, 1, 'w'), complete_frame(fst_step), update_frame_states()])
btn_choose_folder.grid(row=row_choose_folder, column=0, sticky='w', padx=5)

### second step
snd_step_txt = ['Passo 2: Executar Modelo', 'Paso 2: Iniciar Modelo']
row_snd_step = 2
snd_step = LabelFrame(deploy_tab, text=" " + snd_step_txt[lang] + " ", pady=2, padx=5, relief='solid', highlightthickness=5, font=100, fg='darkblue', borderwidth=2)
snd_step.configure(font=(text_font, first_level_frame_font_size, "bold"))
snd_step.grid(column=0, row=row_snd_step, sticky='nesw')
snd_step.columnconfigure(0, weight=1, minsize=label_width)
snd_step.columnconfigure(1, weight=1, minsize=widget_width)

# choose model
lbl_model_txt = ['Modelo', 'Modelo']
row_model = 0
lbl_model = Label(master=snd_step, text=lbl_model_txt[lang], width=1, anchor="w")
lbl_model.grid(row=row_model, sticky='nesw', pady=2)
dpd_options_model = [["MegaDetector 5a", "MegaDetector 5b", "Custom model"], ["MegaDetector 5a", "MegaDetector 5b", "Otro modelo"]]
var_model = StringVar(snd_step)
var_model.set(dpd_options_model[lang][0])
var_model_short = StringVar()
var_model_path = StringVar()
dpd_model = OptionMenu(snd_step, var_model, *dpd_options_model[lang], command=model_options)
dpd_model.configure(width=1)
dpd_model.grid(row=row_model, column=1, sticky='nesw', padx=5)
dsp_model = Label(master=snd_step, textvariable=var_model_short, fg='darkred')

# include subdirectories
lbl_exclude_subs_txt = ["Não processe subdiretórios", "No procesar subcarpetas"]
row_exclude_subs = 1
lbl_exclude_subs = Label(snd_step, text=lbl_exclude_subs_txt[lang], width=1, anchor="w")
lbl_exclude_subs.grid(row=row_exclude_subs, sticky='nesw', pady=2)
var_exclude_subs = BooleanVar()
var_exclude_subs.set(False)
chb_exclude_subs = Checkbutton(snd_step, variable=var_exclude_subs, anchor="w")
chb_exclude_subs.grid(row=row_exclude_subs, column=1, sticky='nesw', padx=5)

# limit detections
row_excl_detecs = 2
var_excl_detecs = BooleanVar()
var_excl_detecs.set(False)

# threshold for model deploy (not grid by deafult)
lbl_md_thresh_txt = ["Confidence threshold", "Umbral de confianza"]
row_md_thresh = 3
lbl_md_thresh = Label(snd_step, text=" ↳ " + lbl_md_thresh_txt[lang], width=1, anchor="w")
var_md_thresh = DoubleVar()
var_md_thresh.set(0.01)
scl_md_thresh = Scale(snd_step, from_=0.005, to=1, resolution=0.005, orient=HORIZONTAL, variable=var_md_thresh, showvalue=0, width=10, length=1)
dsp_md_thresh = Label(snd_step, textvariable=var_md_thresh)
dsp_md_thresh.config(fg="darkred")

# use custom image size
row_use_custom_img_size_for_deploy = 4
var_use_custom_img_size_for_deploy = BooleanVar()
var_use_custom_img_size_for_deploy.set(False)


# use absolute paths
row_abs_path = 6
var_abs_paths = BooleanVar()
var_abs_paths.set(False)

# process images
lbl_process_img_txt = ["Processe todas as imagens na pasta especificada", "Procesar todas las imágenes en carpeta elegida"]
row_process_img = 7
lbl_process_img = Label(snd_step, text=lbl_process_img_txt[lang], width=1, anchor="w")
lbl_process_img.grid(row=row_process_img, sticky='nesw', pady=2)
var_process_img = BooleanVar()
var_process_img.set(False)
chb_process_img = Checkbutton(snd_step, variable=var_process_img, command=toggle_img_frame, anchor="w")
chb_process_img.grid(row=row_process_img, column=1, sticky='nesw', padx=5)

## image option frame (dsiabled by default)
img_frame_txt = ["Opções de imagem", "Opciones de imagen"]
img_frame_row = 8
img_frame = LabelFrame(snd_step, text=" ↳ " + img_frame_txt[lang] + " ", pady=2, padx=5, relief='solid', highlightthickness=5, font=100, borderwidth=1, fg="grey80")
img_frame.configure(font=(text_font, second_level_frame_font_size, "bold"))
img_frame.grid(row=img_frame_row, column=0, columnspan=2, sticky = 'ew')
img_frame.columnconfigure(0, weight=1, minsize=label_width)
img_frame.columnconfigure(1, weight=1, minsize=widget_width)

# use checkpoints
lbl_use_checkpnts_txt = ["Use checkpoints enquanto Executa", "Usar puntos de control mientras se ejecuta"]
row_use_checkpnts = 0
lbl_use_checkpnts = Label(img_frame, text="     " + lbl_use_checkpnts_txt[lang], pady=2, state=DISABLED, width=1, anchor="w")
lbl_use_checkpnts.grid(row=row_use_checkpnts, sticky='nesw')
var_use_checkpnts = BooleanVar()
var_use_checkpnts.set(False)
chb_use_checkpnts = Checkbutton(img_frame, variable=var_use_checkpnts, command=toggle_checkpoint_freq, state=DISABLED, anchor="w")
chb_use_checkpnts.grid(row=row_use_checkpnts, column=1, sticky='nesw', padx=5)

# checkpoint frequency
lbl_checkpoint_freq_txt = ["Frequencia do Checkpoint", "Frecuencia puntos de control"]
row_checkpoint_freq = 1
lbl_checkpoint_freq = tk.Label(img_frame, text="        ↳ " + lbl_checkpoint_freq_txt[lang], pady=2, state=DISABLED, width=1, anchor="w")
lbl_checkpoint_freq.grid(row=row_checkpoint_freq, sticky='nesw')
var_checkpoint_freq = StringVar()
ent_checkpoint_freq = tk.Entry(img_frame, textvariable=var_checkpoint_freq, fg='grey', state=NORMAL, width=1)
ent_checkpoint_freq.grid(row=row_checkpoint_freq, column=1, sticky='nesw', padx=5)
ent_checkpoint_freq.insert(0, f"{eg_txt[lang]}: 500")
ent_checkpoint_freq.bind("<FocusIn>", checkpoint_freq_focus_in)
ent_checkpoint_freq.config(state=DISABLED)

# continue from checkpoint file
lbl_cont_checkpnt_txt = ["Continue do ultimo Checkpoint", "Continuar desde el último punto de control"]
row_cont_checkpnt = 2
lbl_cont_checkpnt = Label(img_frame, text="     " + lbl_cont_checkpnt_txt[lang], pady=2, state=DISABLED, width=1, anchor="w")
lbl_cont_checkpnt.grid(row=row_cont_checkpnt, sticky='nesw')
var_cont_checkpnt = BooleanVar()
var_cont_checkpnt.set(False)
chb_cont_checkpnt = Checkbutton(img_frame, variable=var_cont_checkpnt, state=DISABLED, command=disable_chb_cont_checkpnt, anchor="w")
chb_cont_checkpnt.grid(row=row_cont_checkpnt, column=1, sticky='nesw', padx=5)

# process videos
lbl_process_vid_txt = ["Processe todos os videos na pasta especificada", "Procesar todos los vídeos en la carpeta elegida"]
row_process_vid = 9
lbl_process_vid = Label(snd_step, text=lbl_process_vid_txt[lang], width=1, anchor="w")
lbl_process_vid.grid(row=row_process_vid, sticky='nesw', pady=2)
var_process_vid = BooleanVar()
var_process_vid.set(False)
chb_process_vid = Checkbutton(snd_step, variable=var_process_vid, command=toggle_vid_frame, anchor="w")
chb_process_vid.grid(row=row_process_vid, column=1, sticky='nesw', padx=5)

## video option frame (disabled by default)
vid_frame_txt = ["Opções de Video", "Opciones de vídeo"]
vid_frame_row = 10
vid_frame = LabelFrame(snd_step, text=" ↳ " + vid_frame_txt[lang] + " ", pady=2, padx=5, relief='solid', highlightthickness=5, font=100, borderwidth=1, fg="grey80")
vid_frame.configure(font=(text_font, second_level_frame_font_size, "bold"))
vid_frame.grid(row=vid_frame_row, column=0, columnspan=2, sticky='ew')
vid_frame.columnconfigure(0, weight=1, minsize=label_width)
vid_frame.columnconfigure(1, weight=1, minsize=widget_width)

# dont process all frames
lbl_not_all_frames_txt = ["Não processe todos os frames", "No procesar cada fotograma"]
row_not_all_frames = 0
lbl_not_all_frames = Label(vid_frame, text="     " + lbl_not_all_frames_txt[lang], pady=2, state=DISABLED, width=1, anchor="w")
lbl_not_all_frames.grid(row=row_not_all_frames, sticky='nesw')
var_not_all_frames = BooleanVar()
var_not_all_frames.set(False)
chb_not_all_frames = Checkbutton(vid_frame, variable=var_not_all_frames, command=toggle_nth_frame, state=DISABLED, anchor="w")
chb_not_all_frames.grid(row=row_not_all_frames, column=1, sticky='nesw', padx=5)

# process every nth frame
lbl_nth_frame_txt = ["Analisar cada Nº frame", "Analizar cada Nº fotograma"]
row_nth_frame = 1
lbl_nth_frame = tk.Label(vid_frame, text="        ↳ " + lbl_nth_frame_txt[lang], pady=2, state=DISABLED, width=1, anchor="w")
lbl_nth_frame.grid(row=row_nth_frame, sticky='nesw')
var_nth_frame = StringVar()
ent_nth_frame = tk.Entry(vid_frame, textvariable=var_nth_frame, fg='grey', state=NORMAL, width=1)
ent_nth_frame.grid(row=row_nth_frame, column=1, sticky='nesw', padx=5)
ent_nth_frame.insert(0, f"{eg_txt[lang]}: 10")
ent_nth_frame.bind("<FocusIn>", nth_frame_focus_in)
ent_nth_frame.config(state=DISABLED)

# button start deploy
btn_start_deploy_txt = ["Executar modelo", "Desplegar modelo"]
row_btn_start_deploy = 11
btn_start_deploy = Button(snd_step, text=btn_start_deploy_txt[lang], command=start_deploy)
btn_start_deploy.grid(row=row_btn_start_deploy, column=0, columnspan=2, sticky='ew')

### third step
trd_step_txt = ["Passo 3: Pós Processamento", "Paso 3: Post-Procesado (opcional)"]
trd_step_row = 2
trd_step = LabelFrame(deploy_tab, text=" " + trd_step_txt[lang] + " ", pady=2, padx=5, relief='solid', highlightthickness=5, font=100, fg='darkblue', borderwidth=2)
trd_step.configure(font=(text_font, first_level_frame_font_size, "bold"))
trd_step.grid(column=1, row=trd_step_row, sticky='nesw')
trd_step.columnconfigure(0, weight=1, minsize=label_width)
trd_step.columnconfigure(1, weight=1, minsize=widget_width)

# folder for results
lbl_output_dir_txt = ["Pasta de Destino", "Carpeta de destino"]
row_output_dir = 0
lbl_output_dir = Label(master=trd_step, text=lbl_output_dir_txt[lang], width=1, anchor="w")
lbl_output_dir.grid(row=row_output_dir, sticky='nesw', pady=2)
var_output_dir = StringVar()
var_output_dir.set("")
var_output_dir_short = StringVar()
dsp_output_dir = Label(master=trd_step, textvariable=var_output_dir_short, fg='darkred')
btn_output_dir = Button(master=trd_step, text=browse_txt[lang], width=1, command=lambda: browse_dir(var_output_dir, var_output_dir_short, dsp_output_dir, 25, row_output_dir, 0, 'e'))
btn_output_dir.grid(row=row_output_dir, column=1, sticky='nesw', padx=5)

# separate files
lbl_separate_files_txt = ["Separar arquivos em subpastas", "Separar archivos en subcarpetas"]
row_separate_files = 1
lbl_separate_files = Label(trd_step, text=lbl_separate_files_txt[lang], width=1, anchor="w")
lbl_separate_files.grid(row=row_separate_files, sticky='nesw', pady=2)
var_separate_files = BooleanVar()
var_separate_files.set(False)
chb_separate_files = Checkbutton(trd_step, variable=var_separate_files, command=toggle_sep_frame, anchor="w")
chb_separate_files.grid(row=row_separate_files, column=1, sticky='nesw', padx=5)

## separation frame
sep_frame_txt = ["Opções de separação", "Opciones de separación"]
sep_frame_row = 2
sep_frame = LabelFrame(trd_step, text=" ↳ " + sep_frame_txt[lang] + " ", pady=2, padx=5, relief='solid', highlightthickness=5, font=100, borderwidth=1, fg="grey80")
sep_frame.configure(font=(text_font, second_level_frame_font_size, "bold"))
sep_frame.grid(row=sep_frame_row, column=0, columnspan=2, sticky = 'ew')
sep_frame.columnconfigure(0, weight=1, minsize=label_width)
sep_frame.columnconfigure(1, weight=1, minsize=widget_width)

# method of file placement
lbl_file_placement_txt = ["Método de colocação de arquivo", "Método de desplazamiento de archivo"]
row_file_placement = 0
lbl_file_placement = Label(sep_frame, text="     " + lbl_file_placement_txt[lang], pady=2, width=1, anchor="w")
lbl_file_placement.grid(row=row_file_placement, sticky='nesw')
var_file_placement = IntVar()
var_file_placement.set(2)
rad_file_placement_move = Radiobutton(sep_frame, text=["Copy", "Copiar"][lang], variable=var_file_placement, value=2)
rad_file_placement_move.grid(row=row_file_placement, column=1, sticky='w', padx=5)
rad_file_placement_copy = Radiobutton(sep_frame, text=["Move", "Mover"][lang], variable=var_file_placement, value=1)
rad_file_placement_copy.grid(row=row_file_placement, column=1, sticky='e', padx=5)

# separate per confidence
row_sep_conf = 1
var_sep_conf = BooleanVar()
var_sep_conf.set(False)

## visualize images
row_vis_files = 3
var_vis_files = BooleanVar()
var_vis_files.set(False)

## crop images
row_crp_files = 4
var_crp_files = BooleanVar()
var_crp_files.set(False)

# annotate images
row_yol_files = 5
var_yol_files = BooleanVar()
var_yol_files.set(False)

## subframe for the annotation creation options
annot_create_frame_txt = ["Annotation options", "Opciones de anotación"]
annot_create_frame_row = 6
annot_create_frame = LabelFrame(trd_step, text=" ↳ " + annot_create_frame_txt[lang] + " ", pady=2, padx=5, relief='solid', highlightthickness=5, font=100, borderwidth=1, fg="grey80")
annot_create_frame.configure(font=(text_font, second_level_frame_font_size, "bold"))
annot_create_frame.grid(row=annot_create_frame_row, column=0, columnspan=2, sticky = 'ew')
annot_create_frame.columnconfigure(0, weight=1, minsize=label_width)
annot_create_frame.columnconfigure(1, weight=1, minsize=widget_width)

# uniquify filenames and combine files in one folder
row_uniquify = 0
var_uniquify = BooleanVar()
var_uniquify.set(False)

# method of file placement
row_label_placement = 1
var_label_placement = IntVar()
var_label_placement.set(2)

# create csv files
lbl_csv_txt = ["Exportar resultados para .csv e recuperar metadados", "Exportar a .csv y recuperar los metadatos"]
row_csv = 7
lbl_csv = Label(trd_step, text=lbl_csv_txt[lang], width=1, anchor="w")
lbl_csv.grid(row=row_csv, sticky='nesw', pady=2)
var_csv = BooleanVar()
var_csv.set(False)
chb_csv = Checkbutton(trd_step, variable=var_csv, anchor="w")
chb_csv.grid(row=row_csv, column=1, sticky='nesw', padx=5)

# threshold
lbl_thresh_txt = ["Limite de confiança", "Umbral de confianza"]
row_lbl_thresh = 8
lbl_thresh = Label(trd_step, text=lbl_thresh_txt[lang], width=1, anchor="w")
lbl_thresh.grid(row=row_lbl_thresh, sticky='nesw', pady=2)
var_thresh = DoubleVar()
var_thresh.set(0.2)
scl_thresh = Scale(trd_step, from_=0.01, to=1, resolution=0.01, orient=HORIZONTAL, variable=var_thresh, showvalue=0, width=10, length=1)
scl_thresh.grid(row=row_lbl_thresh, column=1, sticky='ew', padx=10)
dsp_thresh = Label(trd_step, textvariable=var_thresh)
dsp_thresh.config(fg="darkred")
dsp_thresh.grid(row=row_lbl_thresh, column=0, sticky='e', padx=0)

# postprocessing button
btn_start_postprocess_txt = ["Executar pós-processamento", "Post-procesar archivos"]
row_start_postprocess = 9
btn_start_postprocess = Button(trd_step, text=btn_start_postprocess_txt[lang], command=start_postprocess)
btn_start_postprocess.grid(row=row_start_postprocess, column=0, columnspan = 2, sticky='ew')



# main function
def main():
    # initialise start screen
    enable_frame(fst_step)
    disable_frame(snd_step)
    disable_frame(trd_step)

    # run
    root.mainloop()

# executable as script
if __name__ == "__main__":
    main()