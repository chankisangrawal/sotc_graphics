#!/usr/local/sci/python
#************************************************************************
#
#  Plot figures and output numbers for lower stratosphere temperature (LST) section.
#       For BAMS SotC 2016
#
#************************************************************************
#                    SVN Info
# $Rev::                                          $:  Revision of last commit
# $Author::                                       $:  Author of last commit
# $Date::                                         $:  Date of last commit
#************************************************************************
#                                 START
#************************************************************************

import numpy as np
import matplotlib.pyplot as plt

import matplotlib.cm as mpl_cm
import matplotlib as mpl
import matplotlib.path as mpath
from matplotlib.ticker import MultipleLocator

import iris
import iris.quickplot as qplt
import cartopy

import copy
import datetime as dt
import gc

import utils # RJHD utilities
import settings

data_loc = "/data/local/rdunn/SotC/{}/data/SLP/".format(settings.YEAR)
reanalysis_loc = "/data/local/rdunn/SotC/{}/data/RNL/".format(settings.YEAR)
image_loc = "/data/local/rdunn/SotC/{}/images/".format(settings.YEAR)

LEGEND_LOC = 'lower left'
LW = 2

# data sources:
# AAO Obtained at PSD http://www.esrl.noaa.gov/psd/data/correlation/aao.data
# or http://www.cpc.ncep.noaa.gov/products/precip/CWlink/daily_ao_index/aao/shtml
# AO http://www.cpc.ncep.noaa.gov/products/precip/CWlink/daily_ao_index/ao.shtml
# NAO https://climatedataguide.ucar.edu/climate-data/hurrell-north-atlantic-oscillation-nao-index-station-based
# SOI BOM ftp://ftp.bom.gov.au/anon/home/ncc/www/sco/soi/soiplaintext.html

# Winter NAO data calculated using IDL SLP_specialNAOtimeseries.pro script
# HadSLP from www.metoffice.gov.uk/hadobs/hadslp2

#************************************************************************
def read_hadslp(filename):
    '''
    Read monthly HadSLP2 fields, returns cube

    '''


    years = []
    months = []

    # process each line, and separate each month using year/month note
    all_months = []
    with open(filename, 'r') as infile:
        for ll, line in enumerate(infile):

            if len(line.split()) == 2:
                years += [int(line.split()[0])]
                months += [int(line.split()[1])]

                if ll != 0:
                    all_months += [this_month]
                this_month = []

            else:
                this_month += [line.split()]
    # and get the final one!
    all_months += [this_month]
                
    all_months = np.array(all_months).astype(int) / 100. # convert to hPa
    all_months = np.swapaxes(all_months, 1,2) # swap lats and lons around

    all_months = all_months[:,:,::-1] # invert latitudes

    delta = 5.
    latitudes = np.arange(-90, 90 + delta, delta)
    longitudes = np.arange(-180 + delta/2., 180 + delta/2., delta)

    times = np.array([(dt.datetime(years[i],months[i],1,0,0) - dt.datetime(years[0], months[0],1,0,0)).days for i in range(len(years))])

    cube = utils.make_iris_cube_3d(all_months, times, "days since {}-{}-01 00:00:00".format(years[0], months[0]), longitudes, latitudes, "HadSLP", "bar")

    return cube # read_hadslp


#************************************************************************
def read_a_ao(filename, name, skip):
    '''
    Read the AO and AAO data, returns Timeseries

    '''

    all_data = np.genfromtxt(filename, dtype = (float), skip_header = skip)

    years = all_data[:,0]
    months = all_data[:,1]
    data = all_data[:,2]

    times = np.array(years) + ((np.array(months)-1.)/12.)

    return utils.Timeseries(name, times, data) # read_ao

#************************************************************************
def read_soi(filename):
    '''
    Read the SOI data, returns Timeseries

    '''
    try:
        all_data = np.genfromtxt(filename, dtype = (float), skip_header = 9)
    except ValueError:
        # presume last year has incomplete months
        all_data = np.genfromtxt(filename, dtype = (float), skip_header = 9, skip_footer = 1)
    

    years = all_data[:,0]
    data = all_data[:,1:]

    times = np.arange(years[0], years[-1]+1, 1/12.)

    return utils.Timeseries("SOI", times, data.reshape(-1)) # read_a_ao

#************************************************************************
def read_snao(filename):
    '''
    Read the SNAO data, returns Timeseries

    '''

    all_data = np.genfromtxt(filename, dtype = (float), skip_header = 0)

    years = all_data[:,0]
    data = all_data[:,2]

    return utils.Timeseries("SNAO", years, data) # read_snao

#************************************************************************
def read_nao(filename):
    '''
    Read the NAO data, returns Timeseries

    '''

    all_data = np.genfromtxt(filename, dtype = (float), skip_header = 9)

    years = all_data[:,0]
    data = all_data[:,1] # just get DJF column

    return utils.Timeseries("NAO", years, data) # read_nao

#************************************************************************
def plt_bars(ax, ts, text, w = 1./12., invert = False, label = True):
    '''
    Plot the bars on an axes

    :param Axes ax: axes to plot on
    :param Timeseries ts: timeseries object
    :param str text: extra text for plotlabel
    :param float w: width of the bars
    :param bool invert: change order of colours

    '''

    if invert:
        plus = ts.data < 0.0
        minus = ts.data>=0.0
    else:
        plus = ts.data > 0.0
        minus = ts.data<=0.0

    ax.bar(ts.times[plus], ts.data[plus], color = 'r', ec = "r", width = w)
    ax.bar(ts.times[minus], ts.data[minus], color = 'b', ec = "b", width = w)
    ax.axhline(0, c = '0.5', ls = '--')
    if label:
        ax.text(0.02, 0.8, "{} {}".format(text, ts.name), transform = ax.transAxes, fontsize = settings.FONTSIZE*0.7)

    return # plt_months

#************************************************************************
def read_winter_nao(data_loc, years):
    '''
    Read the NAO data, returns Timeseries and smoothed version

    '''

    ts_list = []
    smoothed = []
    
    for y in years:

        all_data = np.genfromtxt(data_loc + "SLP_WinterNAOtimeseries_{}.txt".format(y), dtype = (float), skip_header = 1)

        days = all_data[:,1].astype(int)
        months = all_data[:,0].astype(int)
        years = np.array([y for i in days]).astype(int)
        years[months < 12] = years[months < 12] + 1

        times = np.array([dt.datetime(years[i], months[i], days[i]) for i in range(len(days))])

        data = np.ma.masked_where(all_data[:,2] <=-99.99, all_data[:,2])
                                  
        ts_list += [utils.Timeseries("{}/{}".format(y, int(y[2:])+1), times, data)]

        smoothed  += [np.ma.masked_where(all_data[:,3] <=-99.99, all_data[:,3])]

    return ts_list, smoothed # read_winter_nao

#************************************************************************
def run_all_plots():


    #************************************************************************
    # Timeseries figures - winter NAO
    #   initial run usually only Dec + Jan for recent year

    # tried minor locator

    YEARS = ["2014","2015", "2016"]
    plot_data, smoothed_data = read_winter_nao(data_loc, YEARS)

    fig, (ax1, ax2, ax3) = plt.subplots(3, figsize = (10, 8))

    TEXTS = ["(d)","(e)","(f)"]
    for a, ax in enumerate([ax1, ax2, ax3]):
        year = int(YEARS[a])

        plt_bars(ax, plot_data[a], TEXTS[a], w = 1, invert = False)
        utils.thicken_panel_border(ax)
        ax.xaxis.set_ticks([dt.datetime(year,12,1), dt.datetime(year+1,1,1), dt.datetime(year+1,2,1), dt.datetime(year+1,3,1)])

        ax.plot(plot_data[a].times+dt.timedelta(hours=12), smoothed_data[a], "k-", lw = LW)
        ax.set_xlim([dt.datetime(year,12,1), dt.datetime(year+1,2,1)+dt.timedelta(days=30)])

    ax3.xaxis.set_ticklabels(["Dec","Jan","Feb","Mar"], fontsize = settings.FONTSIZE*0.8)
    ax2.set_ylabel("Winter NAO Index (hPa)", fontsize = settings.FONTSIZE)

    fig.subplots_adjust(right = 0.95, top = 0.95, bottom = 0.05, hspace = 0.001)
    plt.setp([a.get_xticklabels() for a in fig.axes[:-1]], visible=False)

    for ax in [ax1, ax2, ax3]:
        ax.set_ylim([-59,99])

        for tick in ax.yaxis.get_major_ticks():
            tick.label.set_fontsize(settings.FONTSIZE*0.8)

    plt.savefig(image_loc+"SLP_ts_winter_nao{}".format(settings.OUTFMT))
    plt.close()

    #************************************************************************
    # Timeseries figures - different indices

    SOI = read_soi(data_loc + "soiplaintext.html")
    AO = read_a_ao(data_loc + "monthly.ao.index.b50.current.ascii", "AO", 3)
    AAO = read_a_ao(data_loc + "monthly.aao.index.b79.current.ascii", "AAO", 5)
    SNAO = read_snao(data_loc + "emslpncep_to{}_ja_pc1_2mnth_jam.txt".format(settings.YEAR)) # from Chris Folland
    NAO = read_nao(data_loc + "nao_station_seasonal.txt")

    print "note for 2017 - align bars and ticks so tick at bar centre, not in between"
    fig = plt.figure(figsize = (10,7))

    # manually set up the 10 axes
    w=0.42
    h=0.19
    ax1 = plt.axes([0.50-w,0.99-h,w,h])
    ax2 = plt.axes([0.50,  0.99-h,w,h])
    ax3 = plt.axes([0.50-w,0.99-(2*h),w,h],sharex=ax1)
    ax4 = plt.axes([0.50,  0.99-(2*h),w,h],sharex=ax2)
    ax5 = plt.axes([0.50-w,0.99-(3*h),w,h],sharex=ax1)
    ax6 = plt.axes([0.50,  0.99-(3*h),w,h],sharex=ax2)
    ax7 = plt.axes([0.50-w,0.99-(4*h),w,h],sharex=ax1)
    ax8 = plt.axes([0.50,  0.99-(4*h),w,h],sharex=ax2)
    ax9 = plt.axes([0.50-w,0.99-(5*h),w,h],sharex=ax1)
    ax10= plt.axes([0.50,  0.99-(5*h),w,h],sharex=ax2)

    plt_bars(ax1, SOI, "(a)", w = 1./12, invert = True)
    plt_bars(ax3, AO, "(c)", w = 1./12)
    plt_bars(ax5, AAO, "(e)", w = 1./12)
    plt_bars(ax7, NAO, "(g)", w = 1.)
    plt_bars(ax9, SNAO, "(i)", w = 1.)

    ax1.set_xlim([1850, int(settings.YEAR)+1])

    plt_bars(ax2, SOI, "(b)", w = 1./12, invert = True)
    plt_bars(ax4, AO, "(d)", w = 1./12)
    plt_bars(ax6, AAO, "(f)", w = 1./12)
    plt_bars(ax8, NAO, "(h)", w = 0.9)
    plt_bars(ax10, SNAO, "(j)", w = 0.9)

    ax2.set_xlim([2006, int(settings.YEAR)+1])
    for ax in [ax2, ax4, ax6, ax8, ax10]:
        ax.yaxis.tick_right()

    # prettify
    for ax in [ax1, ax3, ax5, ax7, ax9]:
        for tick in ax.xaxis.get_major_ticks():
            tick.label.set_fontsize(settings.FONTSIZE*0.8)
        for tick in ax.yaxis.get_major_ticks():
            tick.label.set_fontsize(settings.FONTSIZE*0.8)
        utils.thicken_panel_border(ax)

    for ax in [ax2, ax4, ax6, ax8, ax10]:
        for tick in ax.xaxis.get_major_ticks():
            tick.label.set_fontsize(settings.FONTSIZE*0.8)
        ax.yaxis.tick_right()
        for tick in ax.yaxis.get_major_ticks():
            tick.label2.set_fontsize(settings.FONTSIZE*0.8)
        utils.thicken_panel_border(ax)

    plt.setp([a.get_xticklabels() for a in fig.axes[:-2]], visible=False)

    ax1.xaxis.set_ticks([1850, 1880, 1910, 1940, 1970, 2000])
    ax2.xaxis.set_ticks([2007, 2010, 2013, 2016])
    ax1.yaxis.set_ticks([-40,0,40])
    ax2.yaxis.set_ticks([-40,0,40])
    ax3.yaxis.set_ticks([-4,0,4])
    ax4.yaxis.set_ticks([-4,0,4])
    ax5.yaxis.set_ticks([-2,0,2])
    ax6.yaxis.set_ticks([-2,0,2])
    ax7.yaxis.set_ticks([-4,0,4])
    ax8.yaxis.set_ticks([-4,0,4])
    ax9.yaxis.set_ticks([-2,0,2])
    ax10.yaxis.set_ticks([-2,0,2])

    minorLocator = MultipleLocator(1)
    ax2.xaxis.set_minor_locator(minorLocator)

    ax1.set_ylim([-40,45])
    ax2.set_ylim([-40,45])
    ax3.set_ylim([-4.5,4.9])
    ax4.set_ylim([-4.5,4.9])

    ax5.set_ylabel("Standard Units", fontsize = settings.FONTSIZE*0.8)

    plt.savefig(image_loc+"SLP_ts{}".format(settings.OUTFMT))

    plt.close()

    #************************************************************************
    # Global map

    cube = read_hadslp(data_loc + "hadslp2r.asc")

    # restrict to 1900 to last full year
    date_constraint = utils.periodConstraint(cube, dt.datetime(1900,1,1),dt.datetime(int(settings.YEAR)+1,1,1)) 
    cube = cube.extract(date_constraint)

    # convert to 1981-2010 climatology.
    clim_constraint = utils.periodConstraint(cube, dt.datetime(1981,1,1),dt.datetime(2011,1,1)) 
    clim_cube = cube.extract(clim_constraint)

    clim_data = clim_cube.data.reshape(-1, 12, clim_cube.data.shape[-2], clim_cube.data.shape[-1])

    # more than 15 years present
    climatology = np.ma.mean(clim_data, axis = 0)
    nyears = np.ma.count(clim_data, axis = 0)
    climatology = np.ma.masked_where(nyears <= 15, climatology) # Kate keeps GT 15.


    # extract final year
    final_year_constraint = utils.periodConstraint(cube, dt.datetime(int(settings.YEAR),1,1), dt.datetime(int(settings.YEAR)+1,1,1)) 
    final_year_cube = cube.extract(final_year_constraint)

    final_year_cube.data = final_year_cube.data - climatology

    # more than 6 months present
    annual_cube = final_year_cube.collapsed(['time'], iris.analysis.MEAN)
    nmonths = np.ma.count(final_year_cube.data, axis = 0)
    annual_cube.data = np.ma.masked_where(nmonths <=6, annual_cube.data)

    bounds = [-100, -8, -4, -2, -1, 0, 1, 2, 4, 8, 100]

    utils.plot_smooth_map_iris(image_loc + "SLP_{}_anoms_hadslp".format(settings.YEAR), annual_cube, settings.COLOURMAP_DICT["circulation"], bounds, "Anomalies from 1981-2010 (hPa)")
    utils.plot_smooth_map_iris(image_loc + "p2.1_SLP_{}_anoms_hadslp".format(settings.YEAR), annual_cube, settings.COLOURMAP_DICT["circulation"], bounds, "Anomalies from 1981-2010 (hPa)", figtext = "(v) Sea Level Pressure")

    plt.close()

    del annual_cube
    del final_year_cube
    gc.collect()

    #************************************************************************
    # Polar Figures (1x3)

    # apply climatology - incomplete end year, so repeat climatology and then trunkate
    climatology = np.tile(climatology, ((cube.data.shape[0]/12)+1,1,1))
    anoms = iris.cube.Cube.copy(cube)

    anoms.data = anoms.data - climatology[0:anoms.data.shape[0], :, :]

    bounds = [-100, -8, -4, -2, -1, 0, 1, 2, 4, 8, 100]

    # set up a 1 x 3 set of axes
    fig = plt.figure(figsize = (5,12))
    plt.clf()

    # set up plot settings
    cmap = settings.COLOURMAP_DICT["circulation"]
    norm=mpl.cm.colors.BoundaryNorm(bounds,cmap.N)
    PLOTYEARS = [2014, 2015, 2016]
    PLOTLABELS = ["(a) 2014/15", "(b) 2015/16", "(c) 2016/17"]

    # boundary circle
    theta = np.linspace(0, 2*np.pi, 100)
    center, radius = [0.5, 0.5], 0.5
    verts = np.vstack([np.sin(theta), np.cos(theta)]).T
    circle = mpath.Path(verts * radius + center)


    # spin through axes
    for a in range(3):  

        ax = plt.subplot(3, 1, a+1, projection=cartopy.crs.NorthPolarStereo())

        plot_cube = iris.cube.Cube.copy(anoms)

        # extract 3 winter months
        date_constraint = utils.periodConstraint(anoms, dt.datetime(PLOTYEARS[a],12,1),dt.datetime(PLOTYEARS[a]+1,3,1)) 
        plot_cube = plot_cube.extract(date_constraint)

        # plot down to equator
        lat_constraint = utils.latConstraint([3,90]) 
        plot_cube = plot_cube.extract(lat_constraint)

        # take the mean
        try:
            plot_cube = plot_cube.collapsed(['time'], iris.analysis.MEAN)
        except iris.exceptions.CoordinateCollapseError:
            pass

        ax.gridlines() #draw_labels=True)
        ax.add_feature(cartopy.feature.LAND, zorder = 0, facecolor = "0.9", edgecolor = "k")
        ax.coastlines()
        ax.set_boundary(circle, transform=ax.transAxes)
        ax.set_extent([-180, 180, 0, 90], cartopy.crs.PlateCarree())

        ext = ax.get_extent() # save the original extent

        mesh = iris.plot.pcolormesh(plot_cube, cmap=cmap, norm = norm, axes = ax)

        ax.set_extent(ext, ax.projection) # fix the extent change from colormesh
        ax.text(-0.05, 1.0, PLOTLABELS[a], fontsize = settings.FONTSIZE * 0.8, transform=ax.transAxes)

    # add a colourbar for the figure
    cbar_ax = fig.add_axes([0.87, 0.07, 0.04, 0.9])
    cb=plt.colorbar(mesh, cax = cbar_ax, orientation = 'vertical', ticks = bounds[1:-1], label = "Anomaly (hPa)", drawedges=True)

    # prettify
    cb.set_ticklabels(["{:g}".format(b) for b in bounds[1:-1]])
    cb.outline.set_color('k')
    cb.outline.set_linewidth(2)
    cb.dividers.set_color('k')
    cb.dividers.set_linewidth(2)


    fig.subplots_adjust(bottom=0.05, top=0.95, left=0.04, right=0.95, wspace=0.02)

    plt.title("")
    fig.text(0.03, 0.95, "", fontsize = settings.FONTSIZE * 0.8)

    plt.savefig(image_loc + "SLP_polar{}".format(settings.OUTFMT))
    plt.close()

    del plot_cube
    del climatology
    gc.collect()

    #************************************************************************
    # SNAO figures


    date_constraint = utils.periodConstraint(anoms, dt.datetime(int(settings.YEAR),7,1),dt.datetime(int(settings.YEAR),9,1)) 
    ja_cube = anoms.extract(date_constraint)
    ja_cube = ja_cube.collapsed(['time'], iris.analysis.MEAN)

    bounds = [-100, -4, -3, -2, -1, 0, 1, 2, 3, 4, 100]
    cmap = settings.COLOURMAP_DICT["circulation"]
    norm=mpl.cm.colors.BoundaryNorm(bounds,cmap.N)
    PLOTLABEL = "(a) July - August"

    fig = plt.figure(figsize = (7,9))
    plt.clf()
    # make axes by hand
    axes = ([0.05,0.45,0.9,0.55],[0.1,0.05,0.88,0.35])

    ax = plt.axes(axes[0], projection=cartopy.crs.Robinson())

    ax.gridlines() #draw_labels=True)
    ax.add_feature(cartopy.feature.LAND, zorder = 0, facecolor = "0.9", edgecolor = "k")
    ax.coastlines()

    mesh = iris.plot.pcolormesh(ja_cube, cmap=cmap, norm = norm, axes = ax)

    ax.text(-0.05, 1.05, PLOTLABEL, fontsize = settings.FONTSIZE * 0.8, transform=ax.transAxes)

    # colorbar
    cb=plt.colorbar(mesh, orientation = 'horizontal', ticks = bounds[1:-1], label = "Anomaly (hPa)", drawedges=True, pad  = 0.05)

    # prettify
    cb.set_ticklabels(["{:g}".format(b) for b in bounds[1:-1]])
    cb.outline.set_color('k')
    cb.outline.set_linewidth(2)
    cb.dividers.set_color('k')
    cb.dividers.set_linewidth(2)

    # and the timeseries
    ax = plt.axes(axes[1])

    snao = np.genfromtxt(data_loc+"emslpncep_to{}_ja_pc1_daily_jam.data".format(settings.YEAR), dtype = (float))

    loc, = np.where(snao[:,0] == int(settings.YEAR))
    data = snao[loc,1:][0]
    times = np.array([dt.datetime(int(settings.YEAR),7,1)+dt.timedelta(days=i) for i in range(len(data))])

    SNAO = utils.Timeseries("Summer NAO Index", times, data)

    plt_bars(ax, SNAO, "", w = 0.7, label = False)
    ax.text(-0.1, 1.05, "(b) Summer NAO Index", fontsize = settings.FONTSIZE * 0.8, transform=ax.transAxes)
    ax.yaxis.set_label("Summer NAO Index")
    # label every 14 days
    ticks =[dt.datetime(int(settings.YEAR),7,1) + dt.timedelta(days=i) for i in range(0,len(data),14)]
    ax.xaxis.set_ticks(ticks)
    ax.xaxis.set_ticklabels([dt.datetime.strftime(t, "%d %b %Y") for t in ticks])
    minorLocator = MultipleLocator(1)
    ax.xaxis.set_minor_locator(minorLocator)

    utils.thicken_panel_border(ax3)

    plt.savefig(image_loc + "SLP_SNAO{}".format(settings.OUTFMT))
    plt.close()

    del ja_cube
    gc.collect()

    #************************************************************************
    # EU figure
    contour = True

    date_constraint = utils.periodConstraint(anoms, dt.datetime(int(settings.YEAR),7,1),dt.datetime(int(settings.YEAR),8,1)) 
    jul_cube = anoms.extract(date_constraint)
    date_constraint = utils.periodConstraint(anoms, dt.datetime(int(settings.YEAR),8,1),dt.datetime(int(settings.YEAR),9,1)) 
    aug_cube = anoms.extract(date_constraint)

    bounds = [-100, -4, -3, -2, -1, 0, 1, 2, 3, 4, 100]
    cmap = settings.COLOURMAP_DICT["circulation"]
    norm=mpl.cm.colors.BoundaryNorm(bounds,cmap.N)
    PLOTLABELS = ["(a) July", "(b) August"]

    fig = plt.figure(figsize = (6,11))
    plt.clf()
    # make axes by hand
    axes = ([0.1,0.65,0.8,0.3],[0.1,0.35,0.8,0.3],[0.1,0.05,0.8,0.25])

    cube_list = [jul_cube, aug_cube]
    for a in range(2):
        ax = plt.axes(axes[a], projection=cartopy.crs.PlateCarree(central_longitude = -10))

        ax.gridlines() #draw_labels=True)
        ax.add_feature(cartopy.feature.LAND, zorder = 0, facecolor = "0.9", edgecolor = "k")
        ax.coastlines()
        ax.set_extent([-70, 40, 30, 80], cartopy.crs.PlateCarree())

        if contour:
            from scipy.ndimage.filters import gaussian_filter
            sigma = 0.5
            cube = cube_list[a]

            cube.data = gaussian_filter(cube.data, sigma)
            mesh = iris.plot.contourf(cube, bounds, cmap=cmap, norm = norm, axes = ax)

        else:
            mesh = iris.plot.pcolormesh(cube_list[a], cmap=cmap, norm = norm, axes = ax)

        ax.text(-0.05, 1.05, PLOTLABELS[a], fontsize = settings.FONTSIZE * 0.8, transform=ax.transAxes)

    # colorbar
    cb=plt.colorbar(mesh, orientation = 'horizontal', ticks = bounds[1:-1], label = "Anomaly (hPa)", drawedges=True)

    # prettify
    cb.set_ticklabels(["{:g}".format(b) for b in bounds[1:-1]])
    cb.outline.set_color('k')
    cb.outline.set_linewidth(2)
    cb.dividers.set_color('k')
    cb.dividers.set_linewidth(2)

    # and the timeseries
    ax3 = plt.axes(axes[2])

    snao = np.genfromtxt(data_loc+"emslpncep_to{}_ja_pc1_daily_jam.data".format(settings.YEAR), dtype = (float))

    loc, = np.where(snao[:,0] == int(settings.YEAR))
    data = snao[loc,1:][0]
    times = np.array([dt.datetime(int(settings.YEAR),7,1)+dt.timedelta(days=i) for i in range(len(data))])

    SNAO = utils.Timeseries("Summer NAO Index", times, data)

    plt_bars(ax3, SNAO, "", w = 0.7, label = False)
    ax3.text(-0.05, 1.05, "(c) Summer NAO Index", fontsize = settings.FONTSIZE * 0.8, transform=ax3.transAxes)
    ax3.yaxis.set_label("Summer NAO Index")
    # label every 14 days
    ticks =[dt.datetime(int(settings.YEAR),7,1) + dt.timedelta(days=i) for i in range(0,len(data),14)]
    ax3.xaxis.set_ticks(ticks)
    ax3.xaxis.set_ticklabels([dt.datetime.strftime(t, "%d %b %Y") for t in ticks])
    minorLocator = MultipleLocator(1)
    ax3.xaxis.set_minor_locator(minorLocator)

    utils.thicken_panel_border(ax3)

    plt.savefig(image_loc + "SLP_NAtlantic{}".format(settings.OUTFMT))
    plt.close()

    del cube
    del anoms
    gc.collect()


    return # run_all_plots

#************************************************************************
if __name__ == "__main__":

    run_all_plots()

#************************************************************************
#                                 END
#************************************************************************