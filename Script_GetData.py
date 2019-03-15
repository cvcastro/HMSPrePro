#-------------------------------------------------------------------------------
# Name:         GetData
# Purpose:      Obtain hydrological and landscape data from Esri Living Atlas
#               for HMS-PrePro tool.
#
# Author:       (c) Cynthia V. Castro 2016
#
# Hosted:       8/8/2016
# Required:     ArcGIS 10.3, Spatial Analyst extension enabled
#-------------------------------------------------------------------------------

import arcpy
from arcpy.sa import *
import os
from os import makedirs
import os.path
from os.path import split, join, splitext, exists
import sys
import zipfile
import ArcHydroTools

# Inputs
inUsername = arcpy.GetParameterAsText(0)
inPassword = arcpy.GetParameterAsText(1)
outDir = arcpy.GetParameterAsText(2)
boundary = arcpy.GetParameterAsText(3)
coords = arcpy.GetParameterAsText(4)

cbArcHydro = arcpy.GetParameterAsText(5)
threshold = arcpy.GetParameterAsText(6)

dem30m = arcpy.GetParameterAsText(7)
dem10m = arcpy.GetParameterAsText(8)
demUser = arcpy.GetParameterAsText(9)

cbNHDPlus = arcpy.GetParameterAsText(10)

# Temp Folder
temp = join(os.path.split(outDir)[0],'temp')
if not exists(temp):
    makedirs(temp)

# Workspace Environment
arcpy.env.workspace = arcpy.env.scratchWorkspace = outDir
arcpy.env.overwriteOutput = True
arcpy.env.outputCoordinateSystem = arcpy.SpatialReference(102008)
arcpy.CheckOutExtension("spatial")

""" Landscape Server """
# Connect to ArcGIS Servers
arcpy.AddMessage("Connecting to ArcGIS servers...")
out_folder_path = 'GIS Servers'

out_elevation = 'Elevation.ags'
server_elevation = 'https://elevation.arcgis.com:443/arcgis/services/'

out_landscape1 = 'Landscape1.ags'
server_landscape1 = 'https://landscape1.arcgis.com:443/arcgis/services/'

out_landscape5 = 'Landscape5.ags'
server_landscape5 = 'https://landscape5.arcgis.com:443/arcgis/services/'

arcpy.mapping.CreateGISServerConnectionFile("USE_GIS_SERVICES",
                                        	    out_folder_path,
                                        	    out_elevation,
                                        	    server_elevation,
                                        	    "ARCGIS_SERVER",
                                        	    username=inUsername,
                                        	    password=inPassword,
                                        	    save_username_password=True)

arcpy.mapping.CreateGISServerConnectionFile("USE_GIS_SERVICES",
                                        	    out_folder_path,
                                        	    out_landscape1,
                                        	    server_landscape1,
                                        	    "ARCGIS_SERVER",
                                        	    username=inUsername,
                                        	    password=inPassword,
                                        	    save_username_password=True)

arcpy.mapping.CreateGISServerConnectionFile("USE_GIS_SERVICES",
                                        	    out_folder_path,
                                        	    out_landscape5,
                                        	    server_landscape5,
                                        	    "ARCGIS_SERVER",
                                        	    username=inUsername,
                                        	    password=inPassword,
                                        	    save_username_password=True)

""" DEM """
# Buffer
arcpy.Buffer_analysis(boundary, "Buffer", "500 Feet", "FULL", "ROUND", "NONE", "", "PLANAR")
# DEM
if not demUser:
    arcpy.AddMessage("Extracting DEM...")
    if str(dem30m) == "true":
        DEM_ImageServer = "GIS Servers\\Elevation\\NED30m.ImageServer"
    if str(dem10m) == "true":
        DEM_ImageServer = "GIS Servers\\Elevation\\WorldElevation\\Terrain.ImageServer"
    arcpy.MakeImageServerLayer_management(DEM_ImageServer, "DEM_Layer")
    arcpy.gp.ExtractByMask_sa("DEM_Layer", "Buffer", "DEM")

if demUser:
    dem = arcpy.CopyRaster_management(demDir, os.path.join(outDir, "userDEM"), "", "", "", "NONE", "NONE", "", "NONE", "NONE")
    arcpy.gp.ExtractByMask_sa("userDEM", "Buffer", "DEM")

""" NHDPlus Data """
if str(cbNHDPlus) == "true":
    # Import the 'Extract Landscape Source Data' Tool
    ##arcpy.ImportToolbox("https://landscape1.arcgis.com/arcgis/services;Tools/ExtractData")
    arcpy.ImportToolbox("https://landscape1.arcgis.com:443/arcgis/services;Tools/ExtractData")

    arcpy.MakeFeatureLayer_management(boundary, "Boundary")

    resultsC = arcpy.ExtractData_ExtractData("NHDPlus V2.1 Seamless Catchments", "Boundary")
    resultsF = arcpy.ExtractData_ExtractData("NHDPlus V2.1 Seamless Flowlines", "Boundary")

    # Extract .ZIP to Folder
    zipfile.ZipFile(open(str(resultsC),'rb')).extractall(os.path.join(temp,'Catchments'))
    zipfile.ZipFile(open(str(resultsF),'rb')).extractall(os.path.join(temp,'Flowlines'))

    # Extract to Geodatabase
    catchments = os.path.join(temp, 'Catchments\Landscape.gdb\NHDPlusV2')
    arcpy.CopyFeatures_management(catchments, os.path.join(outDir,'NHDcatchment'))

    NHDcatchment = os.path.join(outDir,'NHDcatchment')

    flowlines = os.path.join(temp, 'Flowlines\Landscape.gdb\NHDPlusV2')
    arcpy.CopyFeatures_management(flowlines, os.path.join(outDir,'NHDflowline'))

    # Select by Location (Watershed Boundary)
    arcpy.MakeFeatureLayer_management("NHDcatchment", "NHDcatchment")
    arcpy.MakeFeatureLayer_management("NHDflowline", "NHDflowline")

    arcpy.SelectLayerByLocation_management("NHDcatchment", "HAVE_THEIR_CENTER_IN", "Boundary", 0, "NEW_SELECTION")
    arcpy.CopyFeatures_management("NHDcatchment","Basin")

    arcpy.SelectLayerByLocation_management("NHDflowline","HAVE_THEIR_CENTER_IN","Basin",0,"NEW_SELECTION")
    arcpy.CopyFeatures_management("NHDflowline","Flowline")

    # Project Data
    arcpy.AddMessage("Projecting layers...")
    catchment = arcpy.Project_management(os.path.join(outDir,"Basin"), os.path.join(outDir,"Subbasin"), coords, preserve_shape="NO_PRESERVE_SHAPE", max_deviation="")
    flowline = arcpy.Project_management(os.path.join(outDir,"Flowline"), os.path.join(outDir,"Reach"), coords, preserve_shape="NO_PRESERVE_SHAPE", max_deviation="")

    # Field Management
    arcpy.AddMessage("Updating NHD fields...")

    arcpy.AlterField_management(catchment, 'FEATUREID', 'Name', 'Name')
    arcpy.AlterField_management(flowline, 'COMID', 'Name', 'Name')
    arcpy.AlterField_management(flowline, 'FromNode', 'FROM_NODE', 'FROM_NODE')
    arcpy.AlterField_management(flowline, 'ToNode', 'TO_NODE', 'TO_NODE')

    arcpy.AddField_management(flowline, "NextDownID", "LONG", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")

    to_nodes = {}
    from_nodes = {}
    all_Nodes = []
    with arcpy.da.SearchCursor(flowline, ["Name", "FROM_NODE", "TO_NODE"]) as cursor:
        for row in cursor:
            to_nodes[row[0]] = row[2]
            from_nodes[row[1]] = row[0]
            all_Nodes.append(row[1])

    with arcpy.da.UpdateCursor(flowline, ["Name", "FROM_NODE", "TO_NODE", "NextDownID"]) as cursor:
        for row in cursor:
            if to_nodes[row[0]] in all_Nodes:
                row[3] = from_nodes[to_nodes[row[0]]]
            else:
                row[3] = 0
            cursor.updateRow(row)

    # Delete extra layers
    arcpy.Delete_management(os.path.join(outDir,"NHDcatchment"))
    arcpy.Delete_management(os.path.join(outDir,"NHDflowline"))
    arcpy.Delete_management(os.path.join(outDir,"Basin"))
    arcpy.Delete_management(os.path.join(outDir,"Flowline"))

""" ArcHydro Delineation """
if str(cbArcHydro) == "true":
    # Local Variables
    DEM = "DEM"
    STR = os.path.join(temp, "STR")
    STRDEF = os.path.join(temp, "STRDEF")
    STRLNK = os.path.join(temp, "STRLNK")
    GRID = os.path.join(temp, "GRID")
    flowline = os.path.join(outDir, "Flowline")

    # Process:  Fill Sinks
    arcpy.AddMessage("Filling sinks...")
    FIL = Fill(DEM)
    FIL.save(os.path.join(temp, "FIL"))

    # Process:  Flow Direction
    arcpy.AddMessage("Flow Direction Grid...")
    FDR = FlowDirection(os.path.join(temp, "FIL"))
    FDR.save(os.path.join(temp, "FDR"))

    # Process:  Flow Accumulation
    arcpy.AddMessage("Flow Accumulation Grid...")
    FAC = FlowAccumulation(os.path.join(temp, "FDR"))
    FAC.save(os.path.join(temp, "FAC"))

    # Process:  Stream Condition
    arcpy.AddMessage("Stream Condition...")
    STRCON = Con(FAC, 1, "", "Value >="+str(threshold))
    STRCON.save(STR)

    # Process:  Stream Definition
    arcpy.AddMessage("Stream Definition...")
    DEF = StreamOrder(STR, FDR)
    DEF.save(STRDEF)

    # Process:  Stream Segmentation
    arcpy.AddMessage("Stream Segmentation...")
    STRSEG = StreamLink(STRDEF, FDR)
    STRSEG.save(STRLNK)

    # Process:  Drainage Line Processing
    arcpy.AddMessage("Drainage Line Processing...")
    ArcHydroTools.DrainageLineProcessing(STRLNK, FDR, flowline)

    # Process:  Catchment Grid Delineation
    arcpy.AddMessage("Catchment Grid Delineation...")
    CATGRID = Watershed(FDR, STRLNK)
    CATGRID.save(GRID)

    # Process:  Catchment Polygon Processing
    arcpy.AddMessage("Catchment Polygon Processing...")
    ArcHydroTools.CatchmentPolyProcessing(GRID, os.path.join(outDir, "Basin"))

    # Process:  Longest Flowpath
    arcpy.AddMessage("Longest Flowpath Processing...")
    ArcHydroTools.LongestFlowPath(os.path.join(outDir, "Basin"), os.path.join(temp, "FDR"), os.path.join(outDir, "Long"))

    # Project Data
    arcpy.AddMessage("Projecting layers...")
    catchment = arcpy.Project_management(os.path.join(outDir,"Basin"), os.path.join(outDir,"Subbasin"), coords, preserve_shape="NO_PRESERVE_SHAPE", max_deviation="")
    flowline = arcpy.Project_management(os.path.join(outDir,"Flowline"), os.path.join(outDir,"Reach"), coords, preserve_shape="NO_PRESERVE_SHAPE", max_deviation="")
    longest = arcpy.Project_management(os.path.join(outDir,"Long"), os.path.join(outDir,"Longest"), coords, preserve_shape="NO_PRESERVE_SHAPE", max_deviation="")

    # HEC-HMS Basin Map
    arcpy.management.MakeFeatureLayer(catchment,"SubbasinMap")
    arcpy.management.CopyFeatures("SubbasinMap",os.path.join(temp,"basinmap.shp"))
    arcpy.management.Delete("SubbasinMap")

    # Field Management
    arcpy.AddMessage("Updating ArcHydro Fields...")
    arcpy.AddField_management(flowline, "FTYPE", "STRING", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
    arcpy.AddField_management(longest, "DrainID", "LONG", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")

    with arcpy.da.UpdateCursor(flowline, ["FTYPE"]) as cursor:
        for row in cursor:
            row[0] = 'StreamRiver'
            cursor.updateRow(row)

    with arcpy.da.UpdateCursor(longest, ["OBJECTID", "DrainID"]) as cursor:
        for row in cursor:
            row[1] = row[0]
            cursor.updateRow(row)

    GridID = {}
    HydroIDs = []
    with arcpy.da.SearchCursor(flowline, ["HydroID", "GridID"]) as cursor:
        for row in cursor:
            GridID[row[0]] = row[1]
            HydroIDs.append(row[0])

    with arcpy.da.UpdateCursor(flowline, ["NextDownID"]) as cursor:
        for row in cursor:
            if row[0] in HydroIDs:
                row[0] = GridID[row[0]]
            else:
                row[0] = 0
            cursor.updateRow(row)

    arcpy.AlterField_management(catchment, 'GridID', 'Name', 'Name')
    arcpy.AlterField_management(flowline, 'GridID', 'Name', 'Name')
    arcpy.AlterField_management(flowline, 'from_node', 'FROM_NODE', 'FROM_NODE')
    arcpy.AlterField_management(flowline, 'to_node', 'TO_NODE', 'TO_NODE')

    # Delete extra layers
    arcpy.Delete_management(os.path.join(outDir,"APUNIQUEID"))
    arcpy.Delete_management(os.path.join(outDir,"LAYERKEYTABLE"))
    arcpy.Delete_management(os.path.join(outDir,"Reach_FS"))
    arcpy.Delete_management(os.path.join(outDir,"Flowline_FS"))
    arcpy.Delete_management(os.path.join(outDir,"Basin"))
    arcpy.Delete_management(os.path.join(outDir,"Flowline"))
    arcpy.Delete_management(os.path.join(outDir,"Long"))

# Extract Image Server
""" Land Use """
arcpy.AddMessage("Extracting Land Use...")
NLCD_ImageServer = "GIS Servers\\Landscape5\\USA_NLCD_2011.ImageServer"
arcpy.MakeImageServerLayer_management(NLCD_ImageServer,"NLCD_Layer")
arcpy.gp.ExtractByMask_sa("NLCD_Layer", os.path.join(outDir,"Buffer"), os.path.join(outDir,"Land_Use"))

""" Percent Impervious """
arcpy.AddMessage("Extracting Percent Impervious...")
Impervious_ImageServer = "GIS Servers\\Landscape5\\USA_NLCD_Impervious_2011.ImageServer"
arcpy.MakeImageServerLayer_management(Impervious_ImageServer, "Impervious_Layer")
arcpy.gp.ExtractByMask_sa("Impervious_Layer", os.path.join(outDir,"Buffer"), os.path.join(outDir,"Impervious"))

""" Soils HSG, USDA """
arcpy.AddMessage("Extracting Soils HSG...")
USA_Soils_Hydrologic_Group_ImageServer = "GIS Servers\\Landscape5\\USA_Soils_Hydrologic_Group.ImageServer"
arcpy.MakeImageServerLayer_management(USA_Soils_Hydrologic_Group_ImageServer, "USA_Soils_Hydrologic_Group_Layer")
arcpy.gp.ExtractByMask_sa("USA_Soils_Hydrologic_Group_Layer", os.path.join(outDir,"Buffer"), os.path.join(outDir,"SoilsHSG"))

# Delete extra layers
arcpy.Delete_management(os.path.join(outDir,"Buffer"))













