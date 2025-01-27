import os
import csv
from lxml import etree


class Calib2CSV:
    def __init__(self, pathin):
        # Initialisation avec le chemin du fichier XML de calibration
        self.pathin = pathin
        self.pathout = os.path.splitext(pathin)[0] + ".csv"

    def convert(self):
        """
        Convertit le fichier XML de calibration en CSV.
        """
        try:
            # Parse le fichier XML
            tree = etree.parse(self.pathin)
            root = tree.getroot()
        except Exception as e:
            print(f"Erreur lors de l'analyse du fichier XML : {e}")
            return

        # Ouvrir le fichier CSV pour écriture
        with open(self.pathout, 'w', newline='') as csv_result:
            csv_writer = csv.writer(csv_result, delimiter=';')

            # Écrire l'en-tête du CSV
            header = ["KnownConv", "PP_X", "PP_Y", "F", "SzIm_Width", "SzIm_Height",
                      "CDist_X", "CDist_Y", "CoeffDist_1", "CoeffDist_2", "CoeffDist_3",
                      "CoeffDistInv_1", "CoeffDistInv_2", "CoeffDistInv_3", "CoeffDistInv_4"]
            csv_writer.writerow(header)

            # Extraction des informations du fichier XML
            calibration = root.find("CalibrationInternConique")
            if calibration is not None:
                known_conv = calibration.findtext("KnownConv", default="")
                pp = calibration.findtext("PP", default="").split()
                f = calibration.findtext("F", default="")
                sz_im = calibration.findtext("SzIm", default="").split()
                calib_dist = calibration.find("CalibDistortion/ModRad")

                # Récupération des valeurs de calibration
                c_dist = calib_dist.findtext("CDist", default="").split()
                coeff_dist = [cd.text for cd in calib_dist.findall("CoeffDist")]
                coeff_dist_inv = [cdi.text for cdi in calib_dist.findall("CoeffDistInv")]

                # Construction de la ligne à ajouter dans le CSV
                row = [known_conv, pp[0], pp[1], f, sz_im[0], sz_im[1],
                       c_dist[0], c_dist[1], coeff_dist[0], coeff_dist[1], coeff_dist[2],
                       coeff_dist_inv[0], coeff_dist_inv[1], coeff_dist_inv[2], coeff_dist_inv[3]]

                # Écrire la ligne dans le fichier CSV
                csv_writer.writerow(row)
            else:
                print("Erreur : CalibrationInternConique non trouvé dans le fichier XML.")

    @staticmethod
    def aide():
        """
        Affiche l'aide pour l'utilisation de la classe Calib2CSV.
        """
        print("********************")
        print("** Aide CalibrationXML2CSV **")
        print("********************")
        print("Arguments requis :")
        print("\t* string :: {Chemin vers le fichier XML de Calibration}")
