import csv
import os.path
import subprocess
import xml.etree.ElementTree as ET
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication, QVariant, NULL
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QFileDialog
from qgis.core import QgsRasterTransparency, QgsPoint, QgsField, QgsFeature, QgsPointXY, Qgis, QgsVectorLayer, \
    QgsRasterLayer, QgsProject, QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsGeometry, QgsMessageLog
from typing import List, Any

import cv2
import numpy as np

# from pyproj import Transformer
# from .photosequence_micmac import *
from .CALIB2CSV import Calib2CSV
# Initialize Qt resources from file resources.py
from .resources import *
# Import the code for the dialog
from .photosequence_dialog import PhotosequenceDialog


class Photosequence:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """
        Constructor.
        
        :param iface: An interface instance that will be passed to this class,
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'Photosequence_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&photosequence')

        # Check if plugin was started the first time in current QGIS session
        # Must be set in initGui() to survive plugin reloads
        self.first_start = None
        self.transformer = None
        self.data_path = ""

    def init_transformer(self, epsg):
        source_crs = QgsCoordinateReferenceSystem("EPSG:4326")
        target_crs = QgsCoordinateReferenceSystem(f"EPSG:{epsg}")
        self.transformer = QgsCoordinateTransform(source_crs, target_crs, QgsProject.instance())

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('Photosequence', message)

    def add_action(
            self,
            icon_path,
            text,
            callback,
            enabled_flag=True,
            add_to_menu=True,
            add_to_toolbar=True,
            status_tip=None,
            whats_this=None,
            parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            # Adds plugin icon to Plugins toolbar
            self.iface.addToolBarIcon(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/photosequence/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Photoséquence'),
            callback=self.run,
            parent=self.iface.mainWindow())

        # will be set False in run()
        self.first_start = True

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&photosequence'),
                action)
            self.iface.removeToolBarIcon(action)

    def BrowseFilesXml(self, lineEdit, file_type):
        if file_type == 'calibration':
            # pour le fichier de calibration de al caméra
            fname, _ = QFileDialog.getOpenFileName(self.dlg, 'Open Calibration File', self.data_path, 'XML files (*.xml)')
            if fname:
                self.data_path = os.path.dirname(fname)
                lineEdit.setText(fname)
        elif file_type == 'orientation':
            # pour le fichier d'orientation
            fname, _ = QFileDialog.getOpenFileName(self.dlg, 'Open Orientation File', self.data_path, 'XML files (*.xml)')
            if fname:
                self.data_path = os.path.dirname(fname)
                lineEdit.setText(fname)

    def BrowseFilesGPKG(self, lineEdit, file_type):
        if file_type == 'line':
            # pour le fichierde mise en place absolue de caméra
            fname, _ = QFileDialog.getOpenFileName(self.dlg, 'Open line trajectory file', self.data_path,
                                                'GPKG files (*.gpkg)')
            if fname:
                self.data_path = os.path.dirname(fname)
                lineEdit.setText(fname)
        elif file_type == 'point':
            # pour le fichier de calibration de al caméra
            fname, _ = QFileDialog.getOpenFileName(self.dlg, 'Open point trajectory file', self.data_path,
                                                'GPKG files (*.gpkg)')
            if fname:
                self.data_path = os.path.dirname(fname)
                lineEdit.setText(fname)

    def BrowseFilesIMG(self, lineEdit):
        directory = QFileDialog.getExistingDirectory(self.dlg, 'Select image(s) directory', self.data_path,
                                                     options=QFileDialog.ShowDirsOnly)
        if directory:
            self.data_path = directory
            lineEdit.setText(directory)

    def BrowseOutputFile(self, lineEdit):
        directory = QFileDialog.getExistingDirectory(self.dlg, 'Select output directory', self.data_path,
                                                     options=QFileDialog.ShowDirsOnly)
        if directory:
            self.data_path = directory
            lineEdit.setText(directory)

    def add_png_to_qgis_project(self, project_path, png_path, epsg, transparence=False):
        """
        Ajoute une couche d'image PNG à un projet QGIS existant et retourne la couche ajoutée.
        Si 'transparence' est True, applique la transparence sur la couche.
        
        :param project_path: Chemin du projet QGIS existant (.qgs ou .qgz).
        :param png_path: Chemin de l'image PNG à ajouter comme couche raster.
        :param transparence: Booléen indiquant si la transparence doit être appliquée (True ou False).
        :return: La couche raster ajoutée au projet.
        """
        # Charger le projet existant
        project = QgsProject.instance()
        if not project.read(project_path):
            raise IOError(f"Impossible de lire le projet QGIS : {project_path}")

        # Créer une couche raster à partir du PNG
        layer_name = os.path.splitext(os.path.basename(png_path))[0]  # Nom de la couche basé sur le fichier
        raster_layer = QgsRasterLayer(png_path, layer_name)

        if not raster_layer.isValid():
            raise ValueError(f"Erreur : La couche raster basée sur {png_path} n'est pas valide.")

        crs = QgsCoordinateReferenceSystem(f"EPSG:{epsg}")
        raster_layer.setCrs(crs)

        # Ajouter la couche raster au projet
        project.addMapLayer(raster_layer)
        print(f"Couche raster ajoutée : {layer_name}")

        # Si transparence est activée, appliquer la transparence à la couche
        if transparence:
            if raster_layer and isinstance(raster_layer, QgsRasterLayer):
                transparency = raster_layer.renderer().rasterTransparency()
                transparent_pixel = QgsRasterTransparency.TransparentThreeValuePixel()
                transparent_pixel.blue = 0
                transparent_pixel.green = 0
                transparent_pixel.red = 0
                transparent_pixel.percentTransparent = 100
                transparency.setTransparentThreeValuePixelList([transparent_pixel])

                # Rafraîchir la couche pour que la transparence soit appliquée
                raster_layer.triggerRepaint()
                print(f"Transparence appliquée à la couche : {layer_name}")

        # Sauvegarder le projet
        if not project.write():
            raise IOError("Erreur lors de la sauvegarde du projet QGIS.")
        print(f"Projet sauvegardé avec succès : {project_path}")

        # Retourner la couche ajoutée
        return raster_layer

    def get_attribute_values(self, gpkg_path, attribute_name):
        """
        Récupère les valeurs d'un attribut spécifique dans un fichier GeoPackage.
    
        :param gpkg_path: Chemin vers le fichier GeoPackage (.gpkg)
        :param attribute_name: Nom de l'attribut à récupérer
        :return: Liste des valeurs de l'attribut
        """
        layer = QgsVectorLayer(gpkg_path, "MyLayer", "ogr")

        if not layer.isValid():
            raise ValueError(f"Impossible de charger la couche GeoPackage : {gpkg_path}")

        if attribute_name not in layer.fields().names():
            raise ValueError(f"L'attribut '{attribute_name}' n'existe pas dans la couche.")

        attribute_values = [feature[attribute_name] for feature in layer.getFeatures()]
        return np.array(attribute_values)

    def list2pts3D(self, liste_coord, output_file):
        """
        Permet de transformer une liste de coordonnées en fichier XML pour MicMac.
        
        :param liste_coord: Liste de coordonnées x, y, z de taille (3, n), 
                             par exemple : [[x1, x2, ...], [y1, y2, ...], [z1, z2, ...]].
        :param output_file: Chemin du fichier XML à générer.
        :return: Un fichier xml au format MicMac des points pour utiliser mm3d SimplePredict
        """
        # Vérifier que la liste est dans le bon format
        if len(liste_coord) != 3 or not all(len(liste_coord[0]) == len(sublist) for sublist in liste_coord):
            raise ValueError(
                "La liste des coordonnées doit être au format [[x1, x2, ...], [y1, y2, ...], [z1, z2, ...]].")

        # Créer l'élément racine XML
        root = ET.Element("DicoAppuisFlottant")

        # Ajouter les coordonnées au fichier XML
        for i, (x, y, z) in enumerate(zip(*liste_coord), start=1):
            one_appuis_elem = ET.SubElement(root, "OneAppuisDAF")

            # Ajouter l'élément Pt avec les coordonnées x, y, z
            pt_elem = ET.SubElement(one_appuis_elem, "Pt")
            pt_elem.text = f"{x} {y} {z}"

            # Ajouter le nom du point (NamePt)
            name_elem = ET.SubElement(one_appuis_elem, "NamePt")
            name_elem.text = str(i)

            # Ajouter l'incertitude
            incertitude_elem = ET.SubElement(one_appuis_elem, "Incertitude")
            incertitude_elem.text = "1 1 1"

        # Créer l'arbre XML et l'écrire dans le fichier
        tree = ET.ElementTree(root)
        tree.write(output_file, encoding="utf-8", xml_declaration=True)

    def extract_rotation_translation(self, xml_filepath):
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
        translation_vector = np.array(
            [list(map(float, centre.text.split()))]) if centre is not None else None  # Convertir en array (1, 3)

        return rotation_matrix, translation_vector.T

    def csv_to_dict(self, filepath):
        with open(filepath, mode='r') as file:
            reader = csv.DictReader(file, delimiter=';')
            # On retourne le dictionnaire de la première ligne
            return next(reader)

    def World2Camera(self, R, C, P):
        return np.dot(R.T, P - C)

    def Cam2Bundle(self, pt3d):
        return [pt3d[0] / pt3d[2], pt3d[1] / pt3d[2], 1]

    def RadDistOnBundle(self, coeffs, bundle):
        rho2 = bundle[0] ** 2 + bundle[1] ** 2
        delta = sum(c * (rho2 ** (i + 1)) for i, c in enumerate(coeffs))
        return [bundle[0] * (1 + delta), bundle[1] * (1 + delta), 1]

    def Bundle2Pixel(self, f, PP_x, PP_y, bundle):
        return [bundle[0] * f + PP_x, bundle[1] * f + PP_y]

    def TransfoCoord(self, calib, orientation, TablCoord, img):
        """
        Transforme des coordonnées 3D en coordonnées 2D dans une image en appliquant les étapes de la chaîne
        de calibration, de projection et de distorsion.
        
        Cette méthode prend un fichier de calibration (XML), une orientation (matrices de rotation et de translation),
        un tableau de coordonnées 3D, et une image pour produire une liste de points filtrés (en pixels) correspondant
        aux coordonnées projetées dans l'image.
        
        :param calib: Chemin vers le fichier de calibration au format XML.
        :type calib: str
        :param orientation: Chemin vers le fichier contenant les matrices de rotation et de translation.
        :type orientation: str
        :param TablCoord: Tableau numpy contenant les coordonnées 3D à transformer (de forme Nx3).
        :type TablCoord: numpy.ndarray
        :param img: Chemin vers l'image utilisée pour filtrer les points en dehors des dimensions de l'image.
        :type img: str
        
        :return: Un tuple contenant :
            - list: Liste des coordonnées 2D filtrées (QgsPointXY) qui se trouvent à l'intérieur des dimensions de l'image.
            - list: Liste complète des coordonnées 2D projetées (incluant les outliers).
        :rtype: tuple
        
        :notes:
            - Les étapes de transformation incluent :
                1. Transformation du fichier de calibration XML en CSV.
                2. Extraction des matrices de rotation et du vecteur de translation.
                3. Application des distorsions radiales.
                4. Filtrage des points projetés pour ne garder que ceux dans les limites de l'image.
            - Les points hors des dimensions de l'image sont exclus du résultat final.
            - Les coordonnées retournées sont inversées en Y, pour correspondre au coordonées image sur qgis.
        """

        mode = 0  # 0 pour Incertitudes, 1 pour Angles
    
        # Convertir le fichier de calibration XML en CSV
        calib_converter = Calib2CSV(calib)
        calib_converter.convert()  # Convertir le fichier XML en CSV
    
        calib_camera_csv = calib.replace(".xml", ".csv")
    
        # Dictionnaire des variables de calibrations
        data_dict = self.csv_to_dict(calib_camera_csv)
    
        R, C = self.extract_rotation_translation(
            orientation)  # Récupération des matrices de rotation et vecteurs de translation
        coeffs_rad = np.array([float(data_dict['CoeffDist_1']), float(data_dict['CoeffDist_2']),
                               float(data_dict['CoeffDist_3'])])  # Création du vecteur K1, K2, K3
        coeffs_rad_inv = np.array(
            [float(data_dict['CoeffDistInv_1']), float(data_dict['CoeffDistInv_2']), float(data_dict['CoeffDistInv_3']),
             float(data_dict['CoeffDistInv_4'])])
    
        L_Coord = []
    
        for i in range(TablCoord.shape[0]):  # Boucle sur tous les points à transformer
            # World to camera frame
            ptCam = self.World2Camera(R, C, TablCoord[i].reshape((3, 1)))  # Reshape pour vecteurs
            # Camera frame to bundle
            ptBun = self.Cam2Bundle(ptCam)
            # Application des distorsions radiales
            ptDist = self.RadDistOnBundle(coeffs_rad, ptBun)
            # Bundle to pixel
            pt2Dproj = self.Bundle2Pixel(float(data_dict['F']), float(data_dict['CDist_X']),
                                         float(data_dict['CDist_Y']), ptDist)
            L_Coord.append(pt2Dproj)
    
        img2 = cv2.imread(img)
        width, height = img2.shape[1::-1]
    
        # Filtrer les points pour ne garder que ceux dans les dimensions de l'image
        coord_filtered = [coord for coord in L_Coord if 0 <= coord[0] <= width and 0 <= coord[1] <= height]
    
        # Traiter les coordonnées sans outliers
        coord_wo_outliers = []
        for i in range(len(coord_filtered)):
            if not (L_Coord[L_Coord.index(coord_filtered[i]) - 1] in coord_filtered):
                coord_wo_outliers.append(L_Coord[L_Coord.index(coord_filtered[i]) - 1])
                coord_wo_outliers.append(coord_filtered[i])
            else:
                coord_wo_outliers.append(coord_filtered[i])
    
        # Transformation des coordonnées en QgsPointXY
        coord_XY = [QgsPointXY(coord[0], -coord[1]) for coord in coord_wo_outliers]
    
        return coord_XY, L_Coord


    def execute_mm3d_simplepredict(self):
        """
        Exécute la commande MicMac `mm3d SimplePredict`.
        
        Commande exécutée : 
            mm3d SimplePredict "*.JPG" Ori-Absolut/ Points3D.xml
        
        :return: La sortie standard de la commande si elle s'exécute avec succès, ou None si une erreur survient.
        :rtype: str | None
        
        :raises subprocess.CalledProcessError: Si la commande échoue et que `check=True` est activé.
        
        :notes:
            - Les fichiers requis doivent être présents dans les répertoires appropriés pour que la commande aboutisse
              (images JPG, orientation absolue et fichier Points3D.xml).
            - Les logs sont écrits dans la console de QGIS via `QgsMessageLog`.
        """


        # commande micmac 
        command = ['mm3d', 'SimplePredict', '".*.JPG"', 'Ori-Absolut/', 'Points3D.xml']
    
        try:
            # Exécuter la commande et sauver la sortie
            result = subprocess.run(command, capture_output=True, text=True, check=True)
    
            # Log de la sortie standard
            output = result.stdout
            QgsMessageLog.logMessage(f"Commande exécutée avec succès : {output}", "PhotosequenceGen", Qgis.Info)
            return output
        except subprocess.CalledProcessError as e:
            # Log en cas d'erreur
            QgsMessageLog.logMessage(f"Erreur lors de l'exécution : {e.stderr}", "PhotosequenceGen", Qgis.Critical)
            return None


    def creer_projet_qgis(self, outputdir, epsg):
        """
        Crée un projet QGIS  et retourne le chemin d'accès au fichier créé.
    
        Parameters
        ----------
        self : instance
            Instance de la classe qui contient cette méthode.
        outputdir : str
            Chemin du répertoire où le projet QGIS sera créé.
    
        Returns
        -------
        str
            Chemin complet du fichier projet QGIS créé, ou None en cas d'erreur.
        """
        # Vérifier si le dossier de sortie existe
        if not os.path.exists(outputdir):
            print(f"Erreur : Le dossier {outputdir} n'existe pas.")
            return None

        # Vérifier si le chemin est un répertoire
        if not os.path.isdir(outputdir):
            print(f"Erreur : {outputdir} n'est pas un répertoire.")
            return None

        # Nom et chemin complet du fichier projet
        nom_projet = "photosequence.qgz"
        chemin_projet = os.path.join(outputdir, nom_projet)

        # Créer un projet QGIS vierge
        projet = QgsProject.instance()
        projet.clear()  # Nettoyer le projet actuel pour garantir qu'il est vierge
        crs = QgsCoordinateReferenceSystem(f"EPSG:{epsg}")
        projet.setCrs(crs)

        # Enregistrer le projet dans le répertoire spécifié
        if projet.write(chemin_projet):
            print(f"Projet QGIS vierge créé avec succès : {chemin_projet}")
            return chemin_projet
        else:
            print(f"Erreur : Impossible de créer le projet QGIS dans {chemin_projet}.")
            return None

    def creer_points(self, trajectory_file, OutputDir, calib, orientation, img, epsg):
        """
        Permet de créer une couche de points contenant les pinules et les labels de certains points de la trajectoire de l'avion.
        
        :param trajectory_file: Couche vectorielle contenant les données de la trajectoire de vol avec des champs comme 'longitude', 'latitude' et 'alt_m'.
        :type trajectory_file: QgsVectorLayer
        :param OutputDir: Répertoire de sortie où seront enregistrées les données (non utilisé dans cette fonction mais passé par convention).
        :type OutputDir: str
        :param calib: Chemin vers le fichier contenant les paramètres de calibration de la caméra.
        :type calib: str
        :param orientation: Dictionnaire contenant les paramètres d'orientation de la caméra.
        :type orientation: dict
        :param img: Chemin du fichier image à utiliser pour la projection des points.
        :type img: str
        
        :return: Couche vectorielle contenant les points projetés, ajoutée au projet QGIS.
        :rtype: QgsVectorLayer
        """

        if not self.transformer:
            self.init_transformer(epsg)

        # Création de la couche temporaire en mémoire
        point_layer = QgsVectorLayer(f'Point?crs=EPSG:{epsg}', 'points_photosequence', 'memory')
        provider = point_layer.dataProvider()

        # Ajout des champs provenant de la couche trajectory_file
        qgsfields = trajectory_file.fields()
        provider.addAttributes(qgsfields)
        point_layer.updateFields()

        # Boucle pour ajouter les points à la couche
        for feature in trajectory_file.getFeatures():
            longitude = feature['longitude']
            latitude = feature['latitude']
            altitude = feature['alt_m']

            # Transformation des coordonnées en système RGF93
            point_wgs84 = QgsPointXY(longitude, latitude)
            point_proj_wo_z = self.transformer.transform(point_wgs84)
            point_proj = np.array([point_proj_wo_z.x(), point_proj_wo_z.y(), altitude]).reshape(1, 3)

            # Transformation en coordonnées d'image
            _, coord_img = self.TransfoCoord(calib, orientation, point_proj, img)

            img1 = cv2.imread(img)
            width, height = img1.shape[1::-1]

            if 0 <= coord_img[0][0] <= width and 0 <= coord_img[0][1] <= height:
                # Création de l'entité avec les coordonnées de l'image
                new_feature = feature
                new_feature.setGeometry(QgsPoint(coord_img[0][0], -coord_img[0][1]))

                # Copie des attributs de trajecto_layer
                # new_feature.setAttributes([feature[field.name()] for field in qgsfields])

                new_feature['label_posx'] = NULL
                new_feature['label_posy'] = NULL

                # Ajout de l'entité à la couche
                provider.addFeature(new_feature)

        # Application du style à la couche (si le fichier de style existe)
        style_path = os.path.join(os.path.dirname(__file__), "style_bea.qml")
        if os.path.exists(style_path):
            point_layer.loadNamedStyle(style_path)
            point_layer.triggerRepaint()
        else:
            print(f"Erreur : le fichier de style {style_path} n'existe pas.")

        # Ajouter la couche au projet QGIS
        QgsProject.instance().addMapLayer(point_layer)

        # Retourner la couche créée
        return point_layer

    def creer_polygone(self, points_sol, points_air, epsg):
        """
        Permet de créer des polygones pour les points 2 à 2.
        
        Les polygones auront un contour rouge, et leur intérieur sera d'un rouge plus clair. 
        La table attributaire est remplie avec le numéro du point et les coordonnées des points dans les airs.
        
        :param points_sol: Liste des positions de l'avion au sol sous forme de QgsPointXY.
        :type points_sol: List[QgsPointXY]
        :param points_air: Liste des positions de la trace aérienne de l'avion sous forme de QgsPointXY.
        :type points_air: List[QgsPointXY]
        
        :return: Une couche de polygone
        :rtype: QgsVectorLayer
        """

        # Créer une couche de polygones vide
        polygone_layer = QgsVectorLayer(f'Polygon?crs=EPSG:{epsg}', 'Polygones', 'memory')
        provider = polygone_layer.dataProvider()

        # Ajouter les champs pour la table d'attributs
        provider.addAttributes([
            QgsField("num_point", QVariant.Int),
            QgsField("x_air1", QVariant.Double),
            QgsField("y_air1", QVariant.Double),
            QgsField("x_air2", QVariant.Double),
            QgsField("y_air2", QVariant.Double),
        ])
        polygone_layer.updateFields()

        # Ajouter les polygones pour chaque paire de points
        for i in range(min(len(points_sol), len(points_air)) - 1):
            point_sol1 = points_sol[i]
            point_sol2 = points_sol[i + 1]
            point_air1 = points_air[i]
            point_air2 = points_air[i + 1]

            # Créer le polygone
            polygone = QgsGeometry.fromPolygonXY([
                [point_sol1, point_air1, point_air2, point_sol2]
            ])

            # Créer une entité avec les attributs
            feature = QgsFeature()
            feature.setGeometry(polygone)
            feature.setAttributes([
                i + 1,  # Numéro du point
                point_air1.x(), point_air1.y(),  # Coordonnées du premier point aérien
                point_air2.x(), point_air2.y()  # Coordonnées du deuxième point aérien
            ])
            provider.addFeature(feature)

        chemin_script = os.path.abspath(__file__)
        repertoire_script = os.path.dirname(chemin_script)
        style_path = repertoire_script + '/Polygones.qml'
        if not os.path.exists(style_path):
            print(f"Erreur : le fichier de style {style_path} n'existe pas.")

            return

        # Charger le style .qml
        polygone_layer.loadNamedStyle(style_path)

        if not polygone_layer.isValid():
            print("Erreur : le style n'a pas pu être appliqué.")
            return

        # Appliquer le style et redessiner la couche
        polygone_layer.triggerRepaint()

        # Confirmer que le style a été appliqué
        print("Style appliqué avec succès.")

        # Ajouter la couche au projet
        QgsProject.instance().addMapLayer(polygone_layer)

        # Retourner la couche créée
        return polygone_layer

    def reset_dialog(self):
        """Réinitialise les champs de la boîte de dialogue."""
        self.dlg.lineEdit_2.clear()  # Réinitialiser le fichier de calibration
        self.dlg.lineEdit_3.clear()  # Réinitialiser le fichier d'orientation
        self.dlg.lineEdit_4.clear()  # Réinitialiser le fichier image
        self.dlg.lineEdit_6.clear()  # Réinitialiser la trajectoire des points
        self.dlg.lineEdit_7.clear()  # Réinitialiser le répertoire de sortie

    def disconnect_signals(self):
        """Déconnecte les signaux pour éviter les doublons."""
        try:
            self.dlg.toolButton_2.clicked.disconnect()
            self.dlg.toolButton_3.clicked.disconnect()
            self.dlg.toolButton_5.clicked.disconnect()
            self.dlg.toolButton_6.clicked.disconnect()
            self.dlg.toolButton_7.clicked.disconnect()
            self.dlg.rb_micmac.clicked.disconnect()
            self.dlg.rb_classic.clicked.disconnect()
        except TypeError:
            # Si les signaux ne sont pas connectés, ignorer les erreurs
            pass

    def get_image_files(self, directory):
        """
        Parcourt tous les fichiers dans le répertoire spécifié et retourne une liste des chemins des fichiers image
        (avec les extensions .JPG, .PNG, .TIF), triée par ordre alphabétique des noms de fichiers,
        en excluant ceux dont le nom se termine par "_Masq" ou "_masq_merged".
        
        :param directory: Le chemin du répertoire à parcourir.
        :type directory: str
        
        :return: Liste des chemins de fichiers image triée par ordre alphabétique, avec exclusions.
        :rtype: list
        """

        # Vérifier si le répertoire existe
        if not os.path.isdir(directory):
            raise ValueError(f"Le répertoire spécifié n'existe pas : {directory}")

        # Initialiser une liste pour les fichiers image
        image_files = []

        # Extensions d'image acceptées
        valid_extensions = ['.jpg', '.jpeg', '.png', '.tif', '.tiff']

        # Parcourir les fichiers dans le répertoire
        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
            file_ext = os.path.splitext(file_path)[1]

            # Vérifier si c'est un fichier et si l'extension est valide
            if os.path.isfile(file_path) and file_ext.lower() in valid_extensions:
                # Exclure les fichiers dont le nom se termine par "_Masq.ext" ou "_masq_merged.ext"
                if filename.endswith("_Masq" + file_ext) or filename.endswith("_masq_merged" + file_ext):
                    continue
                image_files.append(file_path)

        # Trier la liste par ordre alphabétique des noms de fichiers
        image_files.sort(key=lambda x: os.path.basename(x).lower())

        return image_files

    def get_merged_mask_images(self, directory):
        """
        Récupère les fichiers d'image dans un répertoire qui se terminent par "_masq_merged.png".
        
        :param directory: Le chemin du répertoire à parcourir.
        :type directory: str
        
        :return: Liste des chemins des fichiers image se terminant par "_masq_merged.png".
        :rtype: list
        """

        # Vérifier si le répertoire existe
        if not os.path.isdir(directory):
            raise ValueError(f"Le répertoire spécifié n'existe pas : {directory}")

        # Initialiser une liste pour les fichiers image
        merged_mask_images = []

        # Parcourir les fichiers dans le répertoire
        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)

            # Vérifier si c'est un fichier et si le nom se termine par "_masq_merged.png"
            if os.path.isfile(file_path) and filename.endswith("_masq_merged.png"):
                merged_mask_images.append(file_path)

        return merged_mask_images

    def run(self):
        """Run method that performs all the real work"""

        # Create the dialog with elements (after translation) and keep reference
        # Only create GUI ONCE in callback, so that it will only load when the plugin is started
        if self.first_start == True:
            self.first_start = False
            self.dlg = PhotosequenceDialog()

        # show the dialog
        self.reset_dialog()
        self.dlg.show()

        #permet d'éviter les doublons
        self.disconnect_signals()

        # Connecter les boutons au fichier XML correspondant
        self.dlg.toolButton_2.clicked.connect(
            lambda: self.BrowseFilesXml(self.dlg.lineEdit_2, 'calibration'))  # Bouton pour le fichier de calibration
        self.dlg.toolButton_3.clicked.connect(
            lambda: self.BrowseFilesXml(self.dlg.lineEdit_3, 'orientation'))  # Bouton pour le fichier d'orientation

        #connecter les boutons pour les fichiers images
        self.dlg.toolButton_5.clicked.connect(lambda: self.BrowseFilesIMG(self.dlg.lineEdit_4))
        #connecter les boutons pour les fichiers trajecto
        self.dlg.toolButton_6.clicked.connect(lambda: self.BrowseFilesGPKG(self.dlg.lineEdit_6, 'point'))

        # connecter le bouton repertoire de sortie
        self.dlg.toolButton_7.clicked.connect(lambda: self.BrowseOutputFile(self.dlg.lineEdit_7))

        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if OK was pressed
        if result:

            calibration_file = self.dlg.lineEdit_2.text()
            orientation_file = self.dlg.lineEdit_3.text()
            image_file = self.dlg.lineEdit_4.text()
            point_trajectory_file = self.dlg.lineEdit_6.text()
            OutputDir = self.dlg.lineEdit_7.text()
            epsg = self.dlg.le_epsg.text()
            if not self.transformer:
                self.init_transformer(epsg)

            # Récuperer les coordonnées de l'aéronef dans la BDD de la trajectoire en .gpkg
            posx = self.get_attribute_values(point_trajectory_file, 'longitude')
            posy = self.get_attribute_values(point_trajectory_file, 'latitude')
            posz = self.get_attribute_values(point_trajectory_file, 'alt_m')
            posz_tr = self.get_attribute_values(point_trajectory_file, 'mnt_m')

            # =============================================================================
            # créer le projet QGIS
            # =============================================================================

            project_dir = self.creer_projet_qgis(OutputDir, epsg)

            # =============================================================================
            # gestion de la banque d'image
            # =============================================================================

            images_list = self.get_image_files(image_file)
            print(images_list)

            base_img = images_list[0]
            base_img_lyr = self.add_png_to_qgis_project(project_dir, base_img, epsg)

            # Zoom to first raster layer extent
            extent = base_img_lyr.extent()
            projection = QgsCoordinateTransform(base_img_lyr.crs(),
                                                QgsProject.instance().crs(),
                                                QgsProject.instance())
            self.iface.mapCanvas().setExtent(projection.transform(extent))

            # =============================================================================
            # Gestion des masques
            # =============================================================================

            # Boucle permettant de fusionner les masque micmac des images aux images.
            for i in range(1, len(images_list)):
                # Charger l'image en couleur et le masque
                path_in = images_list[i]
                path_mask = os.path.splitext(path_in)[0] + "_Masq.tif"
                # print(path_mask)
                image_color = cv2.imread(path_in)
                mask = cv2.imread(path_mask, cv2.IMREAD_GRAYSCALE)

                # Vérifier que les dimensions correspondent
                if image_color.shape[:2] != mask.shape:
                    raise ValueError("Les dimensions de l'image couleur et du masque ne correspondent pas.")

                # Convertir le masque en 3 canaux pour l'appliquer sur l'image couleur
                mask_3channel = cv2.merge([mask, mask, mask])

                # Appliquer le masque à l'image couleur
                result = cv2.bitwise_and(image_color, mask_3channel)

                # Sauvegarder ou afficher le résultat
                cv2.imwrite(os.path.splitext(path_in)[0] + "_masq_merged.png", result)
            # Boucle permettant de fusionner les masque micmac des images aux images.
            merged_mask_list = self.get_merged_mask_images(image_file)

            for i in range(len(merged_mask_list)):
                # Ajouter l'image PNG au projet et récupérer la couche
                transparence = True
                raster_layer = self.add_png_to_qgis_project(project_dir, merged_mask_list[i], epsg, transparence)

            # =============================================================================
            # ALGORITHME "MAISON"
            # =============================================================================
            if self.dlg.rb_classic.isChecked():

                # =============================================================================
                #             Trajectoire de l'avion
                # =============================================================================
                # Récupérer les indices des valeurs non NULL et transformer les coordonnées en flottants
                indices_posx_not_null = [i for i, value in enumerate(posx) if
                                         not isinstance(value, QVariant) or not value.isNull()]
                indices_posy_not_null = [i for i, value in enumerate(posy) if
                                         not isinstance(value, QVariant) or not value.isNull()]

                # Permet de trier les valeurs de la BDD pour enlever les valeurs NULL et aussi transformer les coordonnées en flottant
                posx_not_null = [float(value) for value in posx if
                                 not isinstance(value, QVariant) or not value.isNull()]
                posy_not_null = [float(value) for value in posy if
                                 not isinstance(value, QVariant) or not value.isNull()]
                posz_not_null = []
                for i in range(len(posx_not_null)):
                    posz_not_null.append(posz[indices_posx_not_null[i]])

                coord_XY_qgs = []
                for i in (range(len(posx_not_null))):
                    coord_XY_qgs.append(QgsPointXY(posx_not_null[i], posy_not_null[i]))

                coord_proj_air = np.zeros((len(posx_not_null), 3))
                i = 0
                for point in coord_XY_qgs:
                    point_proj = self.transformer.transform(point)
                    coord_proj_air[i] = [point_proj.x(), point_proj.y(), posz_not_null[i]]
                    i += 1
                # print("coord_proj_air: ",coord_proj_air)

                L_coord_image_air, _ = self.TransfoCoord(calibration_file, orientation_file, coord_proj_air, base_img)
                # print("L_coord_image_air: ",L_coord_image_air)
                # self.creer_ligne(L_coord_image_air)

                # =============================================================================
                #             Trace au sol
                # =============================================================================
                posz_not_null_tr = []
                for i in range(len(posx_not_null)):
                    posz_not_null_tr.append(posz_tr[indices_posx_not_null[i]])

                coord_proj_tr = np.zeros((len(posx_not_null), 3))
                i = 0
                for point in coord_XY_qgs:
                    point_proj_tr = self.transformer.transform(point)
                    coord_proj_tr[i] = [point_proj_tr.x(), point_proj_tr.y(), posz_not_null_tr[i]]
                    i += 1

                L_coord_image_tr, _ = self.TransfoCoord(calibration_file, orientation_file, coord_proj_tr, base_img)
                # print("L_coord_image_tr: ",L_coord_image_tr)

                layer_polygone = self.creer_polygone(L_coord_image_tr, L_coord_image_air, epsg)

                trajectory_layer = QgsVectorLayer(point_trajectory_file, "trajecto_fictive", "ogr")
                point_layer = self.creer_points(trajectory_layer, OutputDir, calibration_file, orientation_file,
                                                base_img, epsg)


            # =============================================================================
            # si MicMac est choisi
            # =============================================================================

            elif self.dlg.rb_micmac.isChecked():
                # TODO
                print('oui')
