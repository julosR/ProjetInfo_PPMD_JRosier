from lxml import etree
import sys, os, csv

def main(args):
    # Chemin du fichier XML
    pathin = args[0]
    pathout = os.path.splitext(pathin)[0] + "_appuis.csv"
    
    # Parse le fichier XML
    xml = etree.parse(pathin)
    
    # Création du fichier CSV
    with open(pathout, 'w', newline='') as csvResult:
        csvWrite = csv.writer(csvResult, delimiter=';')
        # En-tête du CSV
        header = ["Num", "Im_X", "Im_Y", "Ter_X", "Ter_Y", "Ter_Z"]
        csvWrite.writerow(header)

        # Parcours des balises <Appuis>
        for appui in xml.xpath("//Verif/Appuis"):
            num = appui.findtext("Num")
            im_coords = appui.findtext("Im").split()
            ter_coords = appui.findtext("Ter").split()

            # Ligne à écrire dans le CSV
            row = [num] + im_coords + ter_coords
            csvWrite.writerow(row)

def aide():
    print("*************************")
    print("**  Aide XML -> CSV  **")
    print("*************************")
    print("Arguments requis :")
    print("\t* string :: {Chemin vers le fichier XML}")

if __name__ == '__main__':
    if len(sys.argv) < 3 or any(arg == '-help' for arg in sys.argv):
        aide()
    else:
        main(sys.argv[1:])
