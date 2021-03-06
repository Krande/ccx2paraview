#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" © Ihor Mirzov, February 2020
Distributed under GNU General Public License v3.0

Converts CalculiX .frd resutls file to ASCII .vtk or XML .vtu format:
python3 ./ccx2paraview/main.py ./examples/other/Ihor_Mirzov_baffle_2D.frd vtk
python3 ./ccx2paraview/main.py ./examples/other/Ihor_Mirzov_baffle_2D.frd vtu

TODO It would be a killer feature if Paraview could
visualize gauss point results from the dat file...
https://public.kitware.com/pipermail/paraview/2013-January/027121.html

TODO Parse DAT files - there are lots of results

TODO XDMF format:
https://github.com/calculix/ccx2paraview/issues/6

"""
import shutil
import os
import logging
import argparse

from . import FRDParser
from . import VTKWriter
from . import VTUWriter
from . import PVDWriter
from . import clean


class Converter:
    """

    :param file_path: Absolute or relative path of .frd file
    :param fmt: Type of export
    :param output_folder: Folder for generated output (optional).
    """
    def __init__(self, file_path, fmt, output_folder=None):

        self.file_path = file_path
        temp = os.path.split(file_path)[-1].split('.')
        self.file_name = temp[0]
        self._output_folder = output_folder
        self.ext = temp[1]
        self.fmt = fmt

    def run(self):
        """

        :return:
        """
        os.makedirs(self.output_folder, exist_ok=True)
        shutil.copy(self.file_path, self.output_file)
        # Parse FRD-file
        relpath = os.path.relpath(self.output_file, start=os.path.dirname(__file__))
        logging.info('Parsing ' + relpath)
        p = FRDParser.Parse(self.output_file)

        # If file contains mesh data
        if p.node_block and p.elem_block:
            times = sorted(set([b.value for b in p.result_blocks]))
            l = len(times)
            if l:
                logging.info('{} time increment{}'.format(l, 's' * min(1, l - 1)))

                """ If model has many time steps - many output files
                will be created. Each output file's name should contain
                increment number padded with zero """
                counter = 1
                times_names = {}  # {increment time: file name, ...}
                for t in sorted(times):
                    if l > 1:
                        ext = '.{:0{width}}.{}'.format(counter, self.fmt, width=len(str(l)))

                    else:
                        ext = '.{}'.format(self.fmt)
                    times_names[t] = self.output_file.replace('.frd', ext)
                    counter += 1

                # For each time increment generate separate .vt* file
                # Output file name will be the same as input
                for t, file_name in times_names.items():
                    relpath = os.path.relpath(file_name, start=os.path.dirname(__file__))
                    logging.info('Writing {}'.format(relpath))
                    if self.fmt == 'vtk':
                        VTKWriter.writeVTK(p, file_name, t)
                    if self.fmt == 'vtu':
                        VTUWriter.writeVTU(p, file_name, t)

                # Write ParaView Data (PVD) for series of VTU files.
                if l > 1 and self.fmt == 'vtu':
                    PVDWriter.writePVD(self.output_file.replace('.frd', '.pvd'), times_names)

            else:
                logging.warning('No time increments!')
                file_name = self.output_file[:-3] + self.fmt
                if self.fmt == 'vtk':
                    VTKWriter.writeVTK(p, file_name, None)
                if self.fmt == 'vtu':
                    VTUWriter.writeVTU(p, file_name, None)
        else:
            logging.warning('File is empty!')

    @property
    def output_folder(self):
        if self._output_folder is None:
            return os.path.join(os.path.dirname(self.file_path), 'results')
        else:
            return os.path.abspath(self._output_folder)

    @property
    def output_file(self):
        return os.path.join(self.output_folder, self.file_name + '.' + self.ext)


if __name__ == '__main__':

    # Configure logging
    logging.basicConfig(level=logging.INFO,
                        format='%(levelname)s: %(message)s')

    # Command line parameters
    parser = argparse.ArgumentParser()
    parser.add_argument('filename', type=str,
                        help='FRD file name with extension')
    parser.add_argument('format', type=str,
                        help='output format: vtu or vtk')
    args = parser.parse_args()

    # Create converter and run it
    if args.format in ['vtk', 'vtu']:
        ccx2paraview = Converter(args.filename, args.format)
        ccx2paraview.run()
    else:
        msg = 'ERROR! Wrong format \"{}\". '.format(args.format) \
              + 'Choose one of: vtk, vtu.'
        print(msg)

    # Delete cached files
    clean.cache()
