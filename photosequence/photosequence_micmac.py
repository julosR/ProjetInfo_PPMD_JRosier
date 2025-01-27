#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# from os.path import exists, join, basename, splitext
import numpy as np
# from scipy.optimize import minimize
# from scipy.linalg import svd
# import MMVII
# from MMVII import *
import ORIENTATION2CSV 
import CALIB2CSV
# import build_micmac_Ori as b
import csv
import xml.etree.ElementTree as ET



def extract_rotation_translation(xml_filepath):
    tree = ET.parse(xml_filepath)
    root = tree.getroot()

    # Extraire la matrice de rotation qui est dans la balise externe
    rotation_matrix = []
    param_rotation = root.find('.//Externe/ParamRotation/CodageMatr')
    if param_rotation is not None:
        rotation_matrix.append(list(map(float, param_rotation.find('L1').text.split())))
        rotation_matrix.append(list(map(float, param_rotation.find('L2').text.split())))
        rotation_matrix.append(list(map(float, param_rotation.find('L3').text.split())))
    
    rotation_matrix = np.array(rotation_matrix)  # Convertir en array (3, 3)

    # Extraire le vecteur de translation (Centre)
    centre = root.find('.//Externe/Centre')
    translation_vector = np.array([list(map(float, centre.text.split()))]) if centre is not None else None  # Convertir en array (1, 3)

    return rotation_matrix, translation_vector.Ts


def csv_to_dict(filepath):
    with open(filepath, mode='r') as file:
        reader = csv.DictReader(file, delimiter=';')
        # On retourne le dictionnaire de la première ligne
        return next(reader)

def World2Camera(R, C, P):
    return np.dot(R.T, P - C)

def Cam2Bundle(pt3d: tuple):
  return [pt3d[0]/pt3d[2],pt3d[1]/pt3d[2],1]

def RadDistOnBundle(coeffs, bundle):
    rho2 = bundle[0]**2 + bundle[1]**2
    delta = sum(c * (rho2**(i + 1)) for i, c in enumerate(coeffs))
    return [bundle[0] * (1 + delta), bundle[1] * (1 + delta),1]


def Bundle2Pixel(f,PP_x,PP_y, bundle: tuple) -> tuple:
  return [ bundle[0]*f + PP_x, bundle[1]*f + PP_y]

def TransfoCoord(calib,orientation,TablCoord):


    mode = 0  # 0 pour Incertitudes, 1 pour Angles
    
    #permet de récuper les coordonéées image et terrain
    ORIENTATION2CSV.main([orientation, mode])
    CALIB2CSV.main([calib])
    
    calib_camera_csv = calib.replace(".xml",".csv")
    
    
    #dictionnaire des variables de calibrations
    data_dict = csv_to_dict(calib_camera_csv)
    

    
    R,C = extract_rotation_translation(orientation) #récupération des matrice de rotation et vecteur translation
    coeffs_rad = np.array([float(data_dict['CoeffDist_1']),float(data_dict['CoeffDist_2']),float(data_dict['CoeffDist_3'])]) #création du vecteur K1,K2,K3
    coeffs_rad_inv = np.array([float(data_dict['CoeffDistInv_1']),float(data_dict['CoeffDistInv_2']),float(data_dict['CoeffDistInv_3']),float(data_dict['CoeffDistInv_4'])])
    # print(coeffs_rad)
    L_Coord = []
    
    for i in range(TablCoord.shape[0]):#Boucle sur tout les points à transformer pour pouvoir les transformer
        # world to camera frame
        ptCam = World2Camera(R,C,TablCoord[i].reshape((3,1)))#reshape pour avoir les coordonées en vecteurs
        # print(ptCam)
        
        # camera frame to bundle
        ptBun = Cam2Bundle(ptCam)
        # print(ptBun)
        
        # apply distortions
        ptDist = RadDistOnBundle(coeffs_rad,ptBun)
        # print(ptDist)
        
        # bundle to pixel
        pt2Dproj = Bundle2Pixel(float(data_dict['F']),float(data_dict['CDist_X']),float(data_dict['CDist_Y']),ptDist)
        # print(pt2Dproj)
        L_Coord.append(pt2Dproj)
    L_Coord_array = np.array(L_Coord).reshape(len(L_Coord),2)
    return L_Coord_array


if __name__ == '__main__':
    # nom des différents fichiers, à changer dans le script du plugin
    im1name = 'DJI_20240530115943_0043_D.JPG'
    orientation_camera = 'Ori-Aspro/Orientation-DJI_20240530115943_0043_D.JPG.xml'
    calib_camera = 'Ori-Aspro/AutoCal_Foc-6700_Cam-FC8482.xml'
    Coord_vraie = np.array([[664.391301138824701,1349.16279674381667],
                            [518.961070050442231,1958.57656789023713]])
    test = np.array([[506612.607507922163,6291122.77791096736,102.120031345772475],
                      [506677.654908844328,6291129.37570180371,19.3491652850209164]])
    
    CoordTest = TransfoCoord(calib_camera,orientation_camera,test)
    print(CoordTest)
    
    # inProj = Proj('epsg:3857')  
    # outProj = Proj('epsg:4326') 
    # x1,y1,z1 = -11705274.6374,4826473.6922,150
    # x2,y2,z2 = transform(inProj,outProj,x1,y1,z1) # deprecated some time later than 2.4
    # print (x2,y2) # `-105.150271116 39.7278572773`