import numpy
import os
import pathlib
import glob


def get_directory_contents(directory):
    dirnames = []
    filenames = []
    for (dirpath, dirnames, filenames) in os.walk(directory):
        # level = dirpath.replace(directory, '').count(os.sep)
        # indent = ' ' * 4 * (level)
        # print('{}{}/'.format(indent, os.path.basename(dirpath)))
        # subindent = ' ' * 4 * (level + 1)
        # for f in filenames:
        #     print('{}{}'.format(subindent, f))
        break
    return dirnames, filenames

def scan_root_directory(directory, search_for='.h5'):

    # LENS = []
    # FAMILY = []
    PATH = []
    FILE = []

    for path, dirs, files in os.walk(directory):
        for f in files:
            file_with_path = path + os.sep + f
            if search_for in file_with_path:
                PATH.append(file_with_path)
                items = file_with_path.split(os.sep)
                FILE.append(items[-1])
                # LENS.append(items[-3])
                # FAMILY.append(items[-4])
    return FILE, PATH

if __name__ == "__main__":
    # LENS, FAMILY, PATH = scan_root_directory("/nobackup/gurb1/srio/DABAM2D/ESRF")
    #
    # for i in range(len(PATH)):
    #     print(">>>", FAMILY[i], LENS[i])

    LENS, FAMILY, FILE, PATH = scan_root_directory("/nobackup/gurb1/srio/DABAM2D/ESRF/C_2D_R320um")


    # for path, dirs, files in os.walk("/nobackup/gurb1/srio/DABAM2D/ESRF"):
    #     # print (">>>>", path)
    #     for f in files:
    #         file_with_path = path + os.sep + f
    #         if '.h5' in file_with_path:
    #             PATH.append(file_with_path)
    #             items = file_with_path.split(os.sep)
    #             LENS.append(items[-3])
    #             FAMILY.append(items[-4])

    for i in range(len(PATH)):
        print(">>>", FAMILY[i], LENS[i], FILE[i]) #,  PATH[i])

    print("Total h5 files found: ", len(FILE))