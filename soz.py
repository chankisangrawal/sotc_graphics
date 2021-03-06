#!/usr/bin/env python
#************************************************************************
#
#  Plot figures and output numbers for Stratospheric Ozone (SOZ) section.
#       For BAMS SotC 2016
#
#************************************************************************
#                    SVN Info
# $Rev:: 29                                       $:  Revision of last commit
# $Author:: rdunn                                 $:  Author of last commit
# $Date:: 2020-08-05 12:12:39 +0100 (Wed, 05 Aug #$:  Date of last commit
#************************************************************************
#                                 START
#************************************************************************

# python3
from __future__ import absolute_import
from __future__ import print_function

import numpy as np
import matplotlib.pyplot as plt

import utils # RJHD utilities
import settings

DATALOC = "{}/{}/data/SOZ/".format(settings.ROOTLOC, settings.YEAR)

#************************************************************************
def read_data(filename):
    """
    Read data from .txt file into Iris cube

    :param str filename: file to process

    :returns: cube
    """
    # use header to hard code the final array shapes
    longitudes = np.arange(0.625, 360.625, 1.25)
    latitudes = np.arange(-89.5, 90.5, 1.)
    
    data = np.ma.zeros((latitudes.shape[0], longitudes.shape[0]))

    # read in the dat
    indata = np.genfromtxt(filename, dtype=(float), skip_header=4)

    this_lat = []
    tl = 0
    # process each row, append until have complete latitude band
    for row in indata:
        this_lat += [r for r in row]

        if len(this_lat) == longitudes.shape[0]:
            # copy into final array and reset
            data[tl, :] = this_lat
            tl += 1
            this_lat = []

    # mask the missing values
    data = np.ma.masked_where(data <= -999.000, data)

    cube = utils.make_iris_cube_2d(data, latitudes, longitudes, "SOZ_anom", "DU")

    return cube # read_data

#************************************************************************
def read_ts(filename):

    indata = np.genfromtxt(filename, skip_header=1)

    years = indata[:, 0]
    mean_val = indata[:, 1]

    ts = utils.Timeseries("SOZ", years, mean_val)

    return ts



#************************************************************************
def run_all_plots():

    #************************************************************************
    # Global Map
    if True:
        cube = read_data(DATALOC + "GSG_{}annual mean_G_ano_ref1998-2008.txt".format(settings.YEAR))

        bounds = [-100, -20, -15, -8, -4, 0, 4, 8, 15, 20, 100]
        bounds = [-200, -90, -40, -15, -5, -1, 1, 5, 15, 40, 90, 200]


        utils.plot_smooth_map_iris(settings.IMAGELOC + "SOZ_{}_anoms".format(settings.YEAR), cube, settings.COLOURMAP_DICT["composition"], bounds, "Anomalies from 1998-2008 (DU)")

        utils.plot_smooth_map_iris(settings.IMAGELOC + "p2.1_SOZ_{}_anoms".format(settings.YEAR), cube, settings.COLOURMAP_DICT["composition"], bounds, "Anomalies from 1998-2008 (DU)", figtext="(z) Stratospheric (Total Column) Ozone")


    #************************************************************************
    # Timeseries (plate 1.1)
    if True:
    #    nh = read_ts(DATALOC + "tozave_60N_90N_3_3.dat")
    #    sh = read_ts(DATALOC + "tozave_90S_60S_10_10.dat")

        nh = read_ts(DATALOC + "NH_polar_ozone.txt")
        sh = read_ts(DATALOC + "SH_polar_ozone.txt")

        fig = plt.figure(figsize=(8, 6))
        plt.clf()

        plt.plot(nh.times, nh.data, "b-", label="March NH")
        plt.plot(sh.times, sh.data, "r-", label="October SH")

        plt.ylabel("total Ozone (DU")
        plt.title("Polar Ozone")

        plt.legend()
        plt.savefig(settings.IMAGELOC + "SOZ_ts{}".format(settings.OUTFMT))

    return # run_all_plots

#************************************************************************
if __name__ == "__main__":

    run_all_plots()

#************************************************************************
#                                 END
#************************************************************************
