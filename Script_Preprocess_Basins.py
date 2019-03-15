import arcpy
from arcpy.sa import *
import os
import sys
import time
from time import strftime

# Inputs
version = arcpy.GetParameterAsText(0)
outDir = arcpy.GetParameterAsText(1)
outFol = arcpy.GetParameterAsText(2)
filename = arcpy.GetParameterAsText(3)
timestep = arcpy.GetParameterAsText(4)
reduction = arcpy.GetParameterAsText(5)

CBcanopy = arcpy.GetParameterAsText(6)
initstorage = arcpy.GetParameterAsText(7)
maxstorage = arcpy.GetParameterAsText(8)

CBcn = arcpy.GetParameterAsText(9)
initabstr = arcpy.GetParameterAsText(10)
CBga = arcpy.GetParameterAsText(11)
initcontent = arcpy.GetParameterAsText(12)
satcontent = arcpy.GetParameterAsText(13)
suction = arcpy.GetParameterAsText(14)
conductivity = arcpy.GetParameterAsText(15)

CBscs = arcpy.GetParameterAsText(16)
CBcnlag = arcpy.GetParameterAsText(17)
CBtr55 = arcpy.GetParameterAsText(28)

CBlag = arcpy.GetParameterAsText(18)
CBcunge = arcpy.GetParameterAsText(19)
manning = arcpy.GetParameterAsText(20)
invert = arcpy.GetParameterAsText(21)
shape = arcpy.GetParameterAsText(22)
width = arcpy.GetParameterAsText(23)
sslope = arcpy.GetParameterAsText(24)
manningL = arcpy.GetParameterAsText(25)
manningR = arcpy.GetParameterAsText(26)

CBclark = arcpy.GetParameterAsText(27)

precip = arcpy.GetParameterAsText(29)
surface = arcpy.GetParameterAsText(30)
sheet = arcpy.GetParameterAsText(31)
n_ch = arcpy.GetParameterAsText(32)
n_ol = arcpy.GetParameterAsText(33)

# Workspace Environment
arcpy.env.workspace = arcpy.env.scratchWorkspace = outDir
arcpy.env.overwriteOutput = True
arcpy.CheckOutExtension("spatial")

# Variables
arcpy.AddMessage("Setting feature variables from input geodatabase...")
arcpy.MakeFeatureLayer_management("Subbasin", "Subbasin")
arcpy.MakeFeatureLayer_management("Reach", "Reach")
arcpy.MakeFeatureLayer_management("Longest", "Longest")
arcpy.MakeRasterLayer_management("DEM", "DEM_Whole")
arcpy.MakeRasterLayer_management("Impervious", "Imperviousness")
arcpy.MakeRasterLayer_management("Land_Use", "LandUse")
arcpy.MakeRasterLayer_management("SoilsHSG", "Soils")

longest = 'Longest'
longestID = 'DrainID'

reach = 'Reach'
reachID = 'Name'

basin = 'Subbasin'
basinID = 'Name'

ToNode = 'to_node'
FromNode = 'from_node'

landuse = 'Land_Use'
soils = "SoilsHSG"
soilsID = 'ClassName'
imperviousness = "Imperviousness"
DEM = "DEM_Whole"

""" Basins """
def basinCoords(basin):
    arcpy.AddField_management(basin, "CENTROID_X", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
    arcpy.AddField_management(basin, "CENTROID_Y", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
    arcpy.CalculateField_management(basin, "CENTROID_X", "!shape.centroid.x!", "PYTHON_9.3", "")
    arcpy.CalculateField_management(basin, "CENTROID_Y", "!shape.centroid.y!", "PYTHON_9.3", "")

def basinArea(basin):
    arcpy.AddField_management(basin, "AreaSqMI", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
    arcpy.CalculateField_management(basin, "AreaSqMI", "!SHAPE.AREA@SQUAREMILES!", "PYTHON_9.3", "")

""" Reaches """
def reachCoords(reach):
    arcpy.AddField_management(reach, "START_X", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
    arcpy.AddField_management(reach, "START_Y", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
    arcpy.AddField_management(reach, "END_X", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
    arcpy.AddField_management(reach, "END_Y", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")

    arcpy.CalculateField_management(reach, "START_X", "!shape.firstPoint.x!", "PYTHON_9.3", "")
    arcpy.CalculateField_management(reach, "START_Y", "!shape.firstPoint.y!", "PYTHON_9.3", "")
    arcpy.CalculateField_management(reach, "END_X", "!shape.lastPoint.x!", "PYTHON_9.3", "")
    arcpy.CalculateField_management(reach, "END_Y", "!shape.lastPoint.y!", "PYTHON_9.3", "")

def reachLength(reach):
    arcpy.AddField_management(reach, "LENGTH_FT", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED","")
    arcpy.CalculateField_management(reach, "LENGTH_FT", "!shape.length@feet!", "PYTHON_9.3", "")

def slopeReach(reach, basin, reachID, basinID):
    arcpy.InterpolateShape_3d("DEM_Whole", reach, "Reach_Interpolated", "", "1", "BILINEAR", "DENSIFY", "0")
    arcpy.AddField_management("Reach_Interpolated", "Z_US", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
    arcpy.AddField_management("Reach_Interpolated", "Z_DS", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")

    arcpy.CalculateField_management("Reach_Interpolated", "Z_US", "!shape.positionAlongLine(0.1,True).firstPoint.z!", "PYTHON_9.3", "")
    arcpy.CalculateField_management("Reach_Interpolated", "Z_DS", "!shape.positionAlongLine(0.85,True).firstPoint.z!", "PYTHON_9.3", "")
    arcpy.AddField_management("Reach_Interpolated", "Slope_Fpf", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")

    arcpy.AddGeometryAttributes_management("Reach_Interpolated", "LENGTH", "FEET_US", "", "")

    with arcpy.da.UpdateCursor("Reach_Interpolated", ["Slope_Fpf", "Z_US","Z_DS","LENGTH"]) as cursor:
        for row in cursor:
            row[0] = round((row[1]*3.28 - row[2]*3.28)/(0.7*(row[3])), 5)
            cursor.updateRow(row)

    with arcpy.da.UpdateCursor("Reach_Interpolated", ["Slope_Fpf"]) as cursor:
        for row0 in cursor:
            if row0[0] <= 0.0005:
                row0[0] = 0.0005
            cursor.updateRow(row0)
    del row0, cursor

    arcpy.AddField_management(reach, "Slope_Fpf", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")

    slope_reach = {}
    with arcpy.da.SearchCursor("Reach_Interpolated", [reachID, "Slope_Fpf"]) as cursor:
        for row0 in cursor:
            slope_reach[row0[0]] = row0[1]
    del row0, cursor

    with arcpy.da.UpdateCursor(reach, [reachID, "Slope_Fpf"]) as cursor:
        for row in cursor:
            row[1] = slope_reach[row[0]]
            cursor.updateRow(row)
    del row, cursor

""" Topology """
def nodeID(reach, reachID, basin, basinID, ToNode):
    arcpy.AddField_management(reach, "NodeID", "LONG", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
    arcpy.AddField_management(basin, "NodeID", "LONG", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")

    tonodes = {}
    with arcpy.da.UpdateCursor(reach, [reachID, ToNode, "NodeID"]) as cursor:
        for row in cursor:
            row[2] = round(row[1],0)
            tonodes.update({row[0]: row[1]})
            cursor.updateRow(row)
    del row, cursor

    with arcpy.da.UpdateCursor(basin, [basinID, "NodeID"]) as cursor:
        for row in cursor:
            if row[0] in reachList:
                row[1] = tonodes[row[0]]
            cursor.updateRow(row)
    del row, cursor

def NextDownID(reach, reachID, FromNode, ToNode):
    fromnode = {}
    fromnodes = []
    with arcpy.da.SearchCursor(reach, [reachID, FromNode]) as cursor:
        for row in cursor:
            fromnode.update({row[1]: row[0]})
            fromnodes.append(row[1])
    del row, cursor

    arcpy.AddField_management(reach, "NextDownID", "LONG", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")

    with arcpy.da.UpdateCursor(reach, [ToNode, "NextDownID"]) as cursor:
        for row in cursor:
            if row[0] in fromnodes:
                row[1]=fromnode[row[0]]
            cursor.updateRow(row)
    del row, cursor

""" SCS Curve Number """
def basinslope(DEM, basin, basinID):
    arcpy.gp.Slope_sa(DEM, "DEM_Slope", "PERCENT_RISE", "")
    arcpy.gp.ZonalStatisticsAsTable_sa(basin, basinID, "DEM_Slope", "Table_Slope", "DATA", "ALL")

    # Slope Table
    slope = {}
    with arcpy.da.SearchCursor("Table_Slope", [basinID, "MEAN"]) as cursor:
        for row in cursor:
            slope[row[0]]=(row[1])
    del row, cursor

    # Append to Subbasin
    arcpy.AddField_management(basin, "Slope", "DOUBLE", "", "", "", "",
                                "NULLABLE", "NON_REQUIRED", "")

    with arcpy.da.UpdateCursor(basin, [basinID, "Slope"]) as cursor:
        for row in cursor:
            row[1]= round(slope[row[0]], 4)
            cursor.updateRow(row)
    del row, cursor

    with arcpy.da.UpdateCursor(basin, [basinID, "Slope"]) as cursor:
        for row in cursor:
            if row[1] < 0.0005:
                row[1]= 0.0005
            else:
                row[1] = row[1]
            cursor.updateRow(row)
    del row, cursor

def impervious(imperviousness, basin, basinID):
    ## Impervious values updated by Esri (July 2016)
    ##arcpy.gp.Reclassify_sa(imperviousness, "Value", '1 100', "Imp_Reclass", "DATA")
    arcpy.gp.ZonalStatisticsAsTable_sa(basin, basinID, imperviousness, "Table_Imp", "DATA", "ALL")

    imp = {}
    imparea = {}
    basins = []
    with arcpy.da.SearchCursor("Table_Imp", [basinID, "MEAN", "AREA"]) as cursor:
        for row in cursor:
            basins.append(row[0])
            imp[row[0]]=row[1]
            imparea[row[0]]=row[2]
    del row, cursor

    # Append Data to Subbasins
    arcpy.AddField_management(basin, "AreaSqM", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
    arcpy.AddField_management(basin, "Imp", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
    arcpy.CalculateField_management(basin, "AreaSqM", "!SHAPE.AREA@SQUAREMETERS!", "PYTHON_9.3", "")

    with arcpy.da.UpdateCursor(basin, [basinID, "Imp", "AreaSqM"]) as cursor:
        for row in cursor:
            if row[0] in basins:
                row[1] = round((imp[row[0]] * imparea[row[0]] / row[2] ),2)
            else:
                row[1] = 0
            cursor.updateRow(row)
    del row, cursor

def reclassLU(landuse):
    reclass = '11 1;21 2;22 5;23 6;24 7;31 9;41 4;42 4;43 4;52 10;71 10;81 3;82 3;90 8;95 8;12 1;72 10;73 10;74 10;51 10'
    arcpy.gp.Reclassify_sa(landuse, "Value", reclass, "LandUse_Reclass", "DATA")

def unionSoilsLU(soils):
    arcpy.RasterToPolygon_conversion("LandUse_Reclass", "LandUse_Poly", "NO_SIMPLIFY", "VALUE")
    arcpy.RasterToPolygon_conversion(soils, "Soils_Poly", "NO_SIMPLIFY", "Value")

    arcpy.Union_analysis("LandUse_Poly #;Soils_Poly #", "LandUseSoils_Union", "ALL", "", "GAPS")
    arcpy.MakeFeatureLayer_management("LandUseSoils_Union", "Union")
    arcpy.SelectLayerByAttribute_management("Union", "NEW_SELECTION", "FID_LandUse_Poly=-1 OR FID_Soils_Poly=-1")
    arcpy.DeleteRows_management("Union")

def CNlookup():
    arcpy.CreateTable_management(outDir, "Table_CNLookup", "", "")
    arcpy.AddField_management("Table_CNLookup", "LandUse", "LONG", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
    arcpy.AddField_management("Table_CNLookup", "Category", "TEXT", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
    arcpy.AddField_management("Table_CNLookup", "Description", "TEXT", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
    arcpy.AddField_management("Table_CNLookup", "A", "LONG", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
    arcpy.AddField_management("Table_CNLookup", "B", "LONG", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
    arcpy.AddField_management("Table_CNLookup", "C", "LONG", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
    arcpy.AddField_management("Table_CNLookup", "D", "LONG", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")

    with arcpy.da.InsertCursor("Table_CNLookup", ["LandUse", "Category", "Description", "A", "B", "C", "D"]) as cursor:
        cursor.insertRow(("1", "Water", "Open Water, Perennial Ice/Snow", "98", "98", "98", "98"))
        cursor.insertRow(("2", "Developed ROW", "Developed Open Space", "68", "79", "86", "89"))
        cursor.insertRow(("3", "Cultivated Pasture", "Hay/Pasture, Cultivated Crops", "49", "69", "79", "84"))
        cursor.insertRow(("4", "Forest", "Deciduous, Evergreen, Mixed, Shrub/Scrub", "30", "55", "70", "77"))
        cursor.insertRow(("5", "Developed - Low Intensity", "Developed - Low Intensity", "51", "68", "79", "84"))
        cursor.insertRow(("6", "Developed - Medium Intensity", "Developed - Medium Intensity", "57", "72", "81", "86"))
        cursor.insertRow(("7", "Developed - High Intensity", "Developed - High Intensity, Barren Land", "77", "85", "90", "92"))
        cursor.insertRow(("8", "Wetlands", "Emergent Herbaceuous Wetlands, Woody Wetlands", "98", "98", "98", "98"))
        cursor.insertRow(("9", "Barren Land", "Barren Land", "76", "85", "90", "93"))
        cursor.insertRow(("10", "Grassland", "Dwarf Scrub, Shrub, Herbaceous, Grassland, Lichen, Moss", "39", "61", "74", "80"))
    del cursor

def indivCN(soils, soilsID):
    arcpy.AddField_management("Union", "CNi", "LONG", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")

    cn = {}
    with arcpy.da.SearchCursor("Table_CNLookup", ["LandUse", "A", "B", "C", "D"]) as cursor:
        for row in cursor:
            LU = row[0]
            A = row[1]
            B = row[2]
            C = row[3]
            D = row[4]
            cn[LU] = (A,B,C,D)
    del row, cursor

    HSGvalue = {}
    with arcpy.da.SearchCursor(soils, ["Value", soilsID]) as cursor:
        for row in cursor:
            HSGvalue[row[0]] = row[1]
    del row, cursor

    with arcpy.da.UpdateCursor("Union", ["CNi", "gridcode", "gridcode_1"]) as cursor:
        for row in cursor:
            if HSGvalue[row[2]] == 'A':
                row[0] = cn[row[1]][0]
            elif HSGvalue[row[2]] == 'B':
                row[0] = cn[row[1]][1]
            elif HSGvalue[row[2]] == 'C':
                row[0] = cn[row[1]][2]
            elif HSGvalue[row[2]] == 'D':
                row[0] = cn[row[1]][3]
            elif HSGvalue[row[2]] == 'A/D':
                row[0] = cn[row[1]][0] * 0.5 + cn[row[1]][3] * 0.5
            elif HSGvalue[row[2]] == 'B/D':
                row[0] = cn[row[1]][1] * 0.5 + cn[row[1]][3] * 0.5
            elif HSGvalue[row[2]] == 'C/D':
                row[0] = cn[row[1]][2] * 0.5 + cn[row[1]][3] * 0.5
            cursor.updateRow(row)
    del row, cursor

    arcpy.FeatureToRaster_conversion("Union", "CNi", "CNraster", "30")

def compCN(basin, basinID, reduction):
    arcpy.gp.ZonalStatisticsAsTable_sa(basin, basinID, "CNraster", "Table_CN", "DATA", "ALL")

    cn = {}
    subbasins = []
    with arcpy.da.SearchCursor("Table_CN", [basinID, "MEAN"]) as cursor:
        for row in cursor:
            cn[row[0]]=(row[1])
            subbasins.append(row[0])
    del row, cursor

    arcpy.AddField_management(basin, "CN", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")

    with arcpy.da.UpdateCursor(basin, [basinID, "CN"]) as cursor:
        for row in cursor:
            if row[0] in subbasins:
                row[1]=round(cn[row[0]]*float(reduction),2)
            else:
                row[1]=80
            cursor.updateRow(row)
    del row, cursor

""" Green and Ampt """
def GAlookup():
    arcpy.CreateTable_management(outDir, "Table_GALookup", "", "")

    arcpy.AddField_management("Table_GALookup", "HSG", "TEXT", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
    arcpy.AddField_management("Table_GALookup", "Porosity_Eff", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
    arcpy.AddField_management("Table_GALookup", "Suction", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
    arcpy.AddField_management("Table_GALookup", "Conductivity", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")

    with arcpy.da.InsertCursor("Table_GALookup", ["HSG", "Porosity_Eff", "Suction", "Conductivity"]) as cursor:
        cursor.insertRow(("A","0.417","1.95","9.276"))
        cursor.insertRow(("B", "0.436","3.50","0.520"))
        cursor.insertRow(("C", "0.389","8.22","0.079"))
        cursor.insertRow(("D", "0.385","12.45","0.024"))
    del cursor

def domHSG(soils, basin, basinID):
    HSGvalue = {}
    with arcpy.da.SearchCursor(soils, ["Value", soilsID]) as cursor:
        for row in cursor:
            HSGvalue[row[0]] = row[1]
    del row, cursor

    arcpy.gp.ZonalStatisticsAsTable_sa(basin, basinID, soils, "Table_Soils", "DATA", "ALL")

    dominantHSG = {}
    subbasin = []
    with arcpy.da.SearchCursor("Table_Soils", [basinID, "MAJORITY"]) as cursor:
        for row in cursor:
            subbasin.append(row[0])
            dominantHSG[row[0]] = HSGvalue[row[1]].encode('ascii','ignore')
    del row, cursor

    arcpy.AddField_management(basin, "HSG", "Text", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")

    with arcpy.da.UpdateCursor(basin, [basinID, "HSG"]) as cursor:
        for row in cursor:
            if row[0] in subbasin:
                row[1] = dominantHSG[row[0]]
            else:
                row[1] = 'C'
            cursor.updateRow(row)
    del cursor, row

    with arcpy.da.UpdateCursor(basin, [basinID, "HSG"]) as cursor:
        for row in cursor:
            if row[1] == 'A/D' or 'B/D' or 'C/D':
                row[1] = 'D'
            cursor.updateRow(row)
    del cursor, row

def GAparams():
    arcpy.AddField_management(basin, "initial", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
    arcpy.AddField_management(basin, "saturated", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
    arcpy.AddField_management(basin, "suction", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
    arcpy.AddField_management(basin, "conductivity", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")

    with arcpy.da.UpdateCursor(basin, ["initial", "saturated", "suction", "conductivity"]) as cursor:
            for row in cursor:
                row[0] = initcontent
                row[1] = satcontent
                row[2] = suction
                row[3] = conductivity
                cursor.updateRow(row)
    del cursor, row

def GAempty():
    arcpy.AddField_management(basin, "initial", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
    arcpy.AddField_management(basin, "saturated", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
    arcpy.AddField_management(basin, "suction", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
    arcpy.AddField_management(basin, "conductivity", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")

    with arcpy.da.UpdateCursor(basin, ["initial", "saturated", "suction", "conductivity"]) as cursor:
            for row in cursor:
                row[0] = 0
                row[1] = 0
                row[2] = 0
                row[3] = 0
                cursor.updateRow(row)
    del cursor, row

def GAvalue():
    greenampt = {}
    with arcpy.da.SearchCursor("Table_GALookup", ["HSG", "Porosity_Eff", "Suction", "Conductivity"]) as cursor:
        for row in cursor:
            greenampt[row[0]] = (row[1], row[2], row[3])
    del row, cursor

    arcpy.AddField_management(basin, "porosity_eff", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")

    # Saturated Content
    with arcpy.da.UpdateCursor(basin, ["saturated"]) as cursor:
        for row in cursor:
            row[0] = satcontent
            cursor.updateRow(row)
    del cursor, row

    # Porosity, Suction, Conductivity
    with arcpy.da.UpdateCursor(basin, ["HSG", "porosity_eff", "suction", "conductivity"]) as cursor:
        for row in cursor:
            row[1] = greenampt[row[0]][0]
            row[2] = greenampt[row[0]][1]
            row[3] = greenampt[row[0]][2]
            cursor.updateRow(row)
    del row, cursor

    # Initial Content
    with arcpy.da.UpdateCursor(basin, ["porosity_eff", "initial", "saturated"]) as cursor:
        for row in cursor:
            row[1] = round(row[0]*(1-row[2]),2)
            cursor.updateRow(row)
    del cursor, row

""" Clark """
def reclassDLU():
    reclassDLU = '1 100;2 100;3 50;4 50;5 75;6 100;7 0;8 100;9 0;10 0'
    arcpy.gp.Reclassify_sa("LandUse_Reclass", "Value", reclassDLU, "DLU_Reclass", "DATA")
    arcpy.gp.ZonalStatisticsAsTable_sa(basin, basinID, "DLU_Reclass", "Table_DLU", "DATA", "ALL")

    DLU = {}
    with arcpy.da.SearchCursor("Table_DLU", [basinID, "MEAN"]) as cursor:
        for row in cursor:
            DLU[row[0]] = round(row[1],2)
    del row, cursor

    # Percent land urbanization (%)
    arcpy.AddField_management(basin, "DLU", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")

    with arcpy.da.UpdateCursor(basin, [basinID, "DLU"]) as cursor:
        for row in cursor:
            row[1] = round(DLU[row[0]], 0)
            cursor.updateRow(row)
    del row, cursor

def clarkParams():
    # Watershed Length to Subbasin Centroid
    """ UPDATE HEC-GEOHMS """
    arcpy.AddField_management(basin, "Lca", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")

    with arcpy.da.UpdateCursor(basin, [basinID, "Lca", "LONGST_FT"]) as cursor:
        for row in cursor:
            row[1] = round(row[2] / 5280 / 2, 3)
            cursor.updateRow(row)
    del row, cursor

    # Watershed Slope (feet/mile)
    arcpy.AddField_management(basin, "So", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")

    with arcpy.da.UpdateCursor(basin, ["So", "Slope"]) as cursor:
        for row in cursor:
            row[0] = round(row[1] / 100 * 5280, 3)
            cursor.updateRow(row)
    del row, cursor

    # Channel Slope (feet/mile)
    arcpy.AddField_management(basin, "D", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")

    with arcpy.da.UpdateCursor(basin, ["D", "So"]) as cursor:
        for row in cursor:
            if row[1] <= 20:
                row[0] = 2.46
            elif 20< row[1] <= 40:
                row[0] = 3.79
            elif row[1] > 40:
                row[0] = 5.12
            cursor.updateRow(row)
    del row, cursor

    # Percent channel conveyance (%)
    arcpy.AddField_management(basin, "DCC", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")

    with arcpy.da.UpdateCursor(basin, ["DCC", "DLU"]) as cursor:
        for row in cursor:
            if row[1] <= 60:
                row[0] = 100
            elif 60 < row[1] <= 70:
                row[0] = 90
            elif 70 < row[1] <= 80:
                row[0] = 80
            elif 80 < row[1] <= 90:
                row[0] = 70
            elif 90 < row[1] <= 100:
                row[0] = 60
            cursor.updateRow(row)
    del row, cursor

    # Percent channel improvement (%)
    arcpy.AddField_management(basin, "DCI", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")

    with arcpy.da.UpdateCursor(basin, ["DCI", "DLU"]) as cursor:
        for row in cursor:
            if row[1] >= 60:
                row[0] = 100
            elif 40< row[1] < 60:
                row[0] = 50
            elif row[1] <= 40:
                row[0] = 0
            cursor.updateRow(row)
    del row, cursor

    # Percent ponding (%)
    arcpy.AddField_management(basin, "DPP", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")

    with arcpy.da.UpdateCursor(basin, ["DPP"]) as cursor:
        for row in cursor:
            row[0] = 0
            cursor.updateRow(row)
    del row, cursor

    # On-site detention (%)
    arcpy.AddField_management(basin, "DET", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")

    with arcpy.da.UpdateCursor(basin, ["DET", "DLU"]) as cursor:
        for row in cursor:
            if row[1] >= 60:
                row[0] = 0
            elif 40< row[1] < 60:
                row[0] = 3
            elif row[1] <= 40:
                row[0] = 10
            cursor.updateRow(row)
    del row, cursor

    # Minimum percent land urbanization (%)
    arcpy.AddField_management(basin, "DLUmin", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")

    with arcpy.da.UpdateCursor(basin, ["DLUmin", "DCC"]) as cursor:
        for row in cursor:
            row[0] = round(11344 * math.pow(row[1], -1.4049), 2)
            cursor.updateRow(row)
    del row, cursor

    # On-site detention (%)
    arcpy.AddField_management(basin, "DLUdet", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")

    with arcpy.da.UpdateCursor(basin, ["DLUdet", "DLU", "DLUmin", "DET"]) as cursor:
        for row in cursor:
            if row[1] - row[3] >= row[2]:
                row[0] = row[1] - row[3]
            elif row[1] > row[2] and row[1] - row[3] < row[2]:
                row[0] = row[2]
            elif row[1] < row[2]:
                row[0] = row[1]
            cursor.updateRow(row)
    del row, cursor

def TC_R():
    # Calculate: TC_R
    arcpy.AddField_management(basin, "TC_R", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")

    with arcpy.da.UpdateCursor(basin, ["TC_R", "DLU", "DLUmin", "DET", "DLUdet", "DCC", "Lca", "So"]) as cursor:
        for row in cursor:
            DLU = row[1]
            DLUmin = row[2]
            DLUdet = row[4]
            DCC = row[5]
            L = row[6] * 2
            S = row[7]
            if DLUdet >= DLUmin:
                row[0] = round(4295 * math.pow(DLUdet,-.678) * math.pow(DCC,-.967) * math.pow(L/math.sqrt(S),.706), 2)
            elif DLU > DLUmin and DLUdet < DLUmin:
                row[0] = round(4295 * math.pow(DLUmin,-.678) * math.pow(DCC,-.967) * math.pow(L/math.sqrt(S),.706), 2)
            elif DLU < DLUmin:
                row[0] = round(7.25 * math.pow(L/math.sqrt(S), .706), 2)
            cursor.updateRow(row)
    del row, cursor

    # Calculate: Clark TC
    arcpy.AddField_management(basin, "TC_clark", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")

    with arcpy.da.UpdateCursor(basin, ["TC_clark", "DLU", "DLUmin", "DET", "D", "DCI", "DLUdet", "Lca", "So"]) as cursor:
        for row in cursor:
            DLU = row[1]
            DLUmin = row[2]
            DET = row[3]
            D = row[4]
            DCI = row[5]
            DLUdet = row[6]
            Lca = row[7]
            S = row[8]
            if DLU - DET >= DLUmin:
                row[0] = round(D * (1 - .0062 * (0.7*DCI + 0.3*DLUdet)) * math.pow(Lca/math.sqrt(S),1.06), 2)
            elif DLU > DLUmin and DLU - DET < DLUmin:
                row[0] = round(D * (1 - .0062 * (0.7*DCI + 0.3*DLUmin)) * math.pow(Lca/math.sqrt(S),1.06), 2)
            elif DLU < DLUmin:
                row[0] = round(D * (1 - .0062 * (0.7*DCI + 0.3*DLU)) * math.pow(Lca/math.sqrt(S),1.06), 2)
            cursor.updateRow(row)
    del row, cursor

    with arcpy.da.UpdateCursor(basin, ["TC_clark"]) as cursor:
        for row in cursor:
            if row[0] <= 0.1:
                row[0] = 0.1
            cursor.updateRow(row)
    del row, cursor

    # Calculate: Clark R
    arcpy.AddField_management(basin, "R_init", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")

    with arcpy.da.UpdateCursor(basin, ["R_init", "TC_clark", "TC_R"]) as cursor:
        for row in cursor:
            row[0] = row[2] - row[1]
            if row[1] == 0:
                row[1] = 0.01
            cursor.updateRow(row)
    del row, cursor

    arcpy.AddField_management("Subbasin", "ratio", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")

    with arcpy.da.UpdateCursor(basin, ["ratio", "R_init", "TC_clark"]) as cursor:
        for row in cursor:
            row[0] = round(row[1] / row[2], 0)
            cursor.updateRow(row)
    del row, cursor

    with arcpy.da.UpdateCursor(basin, ["ratio"]) as cursor:
        for row in cursor:
            if row[0] > 6:
                row[0] = 6
            elif row[0] <= 2:
                row[0] = 2
            cursor.updateRow(row)
    del row, cursor

    arcpy.AddField_management(basin, "R_clark", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")

    with arcpy.da.UpdateCursor(basin, ["R_clark", "TC_clark", "ratio"]) as cursor:
        for row in cursor:
            row[0] = round(row[1] * row[2], 2)
            cursor.updateRow(row)
    del row, cursor

def clarkempty():
    arcpy.AddField_management(basin, "TC_clark", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
    arcpy.AddField_management(basin, "R_clark", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")

    with arcpy.da.UpdateCursor(basin, ["TC_clark", "R_clark"]) as cursor:
            for row in cursor:
                row[0] = 0
                row[1] = 0
                cursor.updateRow(row)
    del cursor, row

""" CN Lag Time """
def longestFT(basin, reachID, basinID):
    arcpy.AddField_management(longest, "LONGST_FT", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED","")
    arcpy.CalculateField_management(longest, "LONGST_FT", "!shape.length@feet!", "PYTHON_9.3", "")

    longestFT = {}
    with arcpy.da.SearchCursor(longest, [longestID, "LONGST_FT"]) as cursor:
        for row in cursor:
            longestFT.update({row[0]: row[1]})
    del row, cursor

    arcpy.AddField_management(basin, "LONGST_FT", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED","")

    with arcpy.da.UpdateCursor(basin, [basinID, "LONGST_FT"]) as cursor:
        for row in cursor:
            row[1] = longestFT[row[0]]
            cursor.updateRow(row)
    del row, cursor

def CNlag(basin, reach, timestep):
    arcpy.AddField_management(basin, "CNlag", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
    arcpy.AddField_management(basin, "lag_min", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
    arcpy.AddField_management(basin, "lag_hrs", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")

    with arcpy.da.UpdateCursor(basin, ["CNlag", "LONGST_FT", "CN", "Slope"]) as cursor:
        for row in cursor:
            l = row[1]
            CN = row[2]
            s = row[3]
            row[0] = round((math.pow(l,0.8)*math.pow(1000/CN-9,0.7))/(1900*math.pow(s,0.5))*60,3)
            cursor.updateRow(row)
    del row, cursor

    # Minimum Lag Time
    ###  lag time is greater of NRCS lag or (3.5 * HMS time step)
    with arcpy.da.UpdateCursor(basin, ["CNlag", "lag_min"]) as cursor:
        for row in cursor:
            if row[0] < 3.5 * float(timestep):
                row[1] = round(3.5 * float(timestep),3)
            else:
                row[1] = row[0]
            cursor.updateRow(row)
    del row, cursor

    with arcpy.da.UpdateCursor(basin, ["lag_min", "lag_hrs"]) as cursor:
        for row in cursor:
            row[1] = round(row[0]/60,3)
            cursor.updateRow(row)
    del row, cursor

    lag = {}
    with arcpy.da.SearchCursor(basin, [basinID, "lag_min"]) as cursor:
        for row in cursor:
            lag.update({row[0]: row[1]})
    del row, cursor

    arcpy.AddField_management(reach, "lag_min", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")

    subbasins = []
    with arcpy.da.SearchCursor(basin, [basinID]) as cursor:
        for row in cursor:
            subbasins.append(row[0])
    del row, cursor

    with arcpy.da.UpdateCursor(reach, [reachID, "lag_min"]) as cursor:
        for row in cursor:
            if row[0] in subbasins:
                row[1] = lag[row[0]]
            cursor.updateRow(row)
    del row, cursor

""" TR-55 Lag Time """
def TR55fields(longest):
    arcpy.AddField_management(longest, "Precip2yr", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
    arcpy.AddField_management(longest, "Surface", "TEXT", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
    arcpy.AddField_management(longest, "K", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")

    arcpy.AddField_management(longest, "n_ch", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
    arcpy.AddField_management(longest, "n_ol", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")

    arcpy.AddField_management(longest, "R", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")

    arcpy.AddField_management(longest, "L_sh", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
    arcpy.AddField_management(longest, "L_sc", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
    arcpy.AddField_management(longest, "L_ch", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")

    arcpy.AddField_management(longest, "S_sh", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
    arcpy.AddField_management(longest, "S_sc", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
    arcpy.AddField_management(longest, "S_ch", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")

    arcpy.AddField_management(longest, "t_sh", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
    arcpy.AddField_management(longest, "t_sc", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
    arcpy.AddField_management(longest, "t_ch", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
    arcpy.AddField_management(longest, "t_c", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
    arcpy.AddField_management(longest, "t_l_hrs", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
    arcpy.AddField_management(longest, "t_l_mins", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")

    with arcpy.da.UpdateCursor(longest, ["L_sh", "Precip2yr", "Surface", "n_ch", "n_ol"]) as cursor:
        for row in cursor:
            row[0] = sheet
            row[1] = precip
            row[2] = surface
            row[3] = n_ch
            row[4] = n_ol
            cursor.updateRow(row)
    del row, cursor

    with arcpy.da.UpdateCursor(longest, ["Surface", "K"]) as cursor:
        for row in cursor:
            if row[0] == "Unpaved":
                row[1] = 16.13
            elif row[0] == "Paved":
                row[1] = 20.32
            cursor.updateRow(row)
    del row, cursor

def TR55LengthEst(longest):
    with arcpy.da.UpdateCursor(longest, ["L_sh", "L_sc", "L_ch", "LONGST_FT"]) as cursor:
        for row in cursor:
            row[1] = round((row[3]-row[0])*2/5,2)
            row[2] = round((row[3]-row[0])*3/5,2)
            cursor.updateRow(row)
    del row, cursor

def TR55pts():
    points = []
    with arcpy.da.SearchCursor(longest, ["shape@", "L_sh", "L_sc", "L_ch"]) as cursor:
        for row in cursor:
            point0 = row[0].positionAlongLine(0, True)
            point1 = row[0].positionAlongLine(row[1])
            point2 = row[0].positionAlongLine(row[1]+row[2])
            point3 = row[0].positionAlongLine(1,True)
            points.append(point1)
            points.append(point2)
    del row, cursor

    points = arcpy.CopyFeatures_management(points, 'TR55pts')

def TR55join(longest, longestID):
    arcpy.AddField_management('TR55pts', "PtName", "TEXT", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
    arcpy.SpatialJoin_analysis(longest, "TR55pts", "spatialjoin", join_operation="JOIN_ONE_TO_MANY", join_type="KEEP_COMMON", field_mapping="""PtName "PtName" true true false 255 Text 0 0 ,First,#,TR55pts,PtName,-1,-1;DrainID "DrainID" true true false 255 Text 0 0 ,First,#,TR55pts,DrainID,-1,-1""", match_option="INTERSECT", search_radius="", distance_field_name="")

    pt_name = {}
    with arcpy.da.SearchCursor("spatialjoin", ["JOIN_FID", longestID]) as cursor:
        for row in cursor:
            pt_name[row[0]] = row[1]
    del row, cursor

    with arcpy.da.UpdateCursor("TR55pts", ["OBJECTID", "PtName"]) as cursor:
        for row in cursor:
            row[1] = pt_name[row[0]]
            cursor.updateRow(row)
    del row, cursor

""" .BASIN Script """
def tr55Script(filename):
    localdate = strftime("%d %B %Y")
    localtime = strftime("%H:%M:%S")

    script.write("Basin: {}\n".format(filename))
    script.write("     Last Modified Date:  "+localdate+"\n")
    script.write("     Last Modified Time:  "+localtime+"\n")
    script.write("     Version {}\n".format(version))
    script.write("     Define TR-55 point transitions from shallow-concentrated to channelized flow \n")
    script.write("     Update R (hydraulic radius) using 3D Analyst \n")
    script.write("     Update Manning's n values for channels and overland flow \n")
    script.write("     Run TR-55 script to obtain .BASIN output file \n")
    script.write("\n")
    script.close()

def basinScript(filename):
    localdate = strftime("%d %B %Y")
    localtime = strftime("%H:%M:%S")

    script.write("Basin: {}\n".format(filename))
    script.write("     Last Modified Date:  "+localdate+"\n")
    script.write("     Last Modified Time:  "+localtime+"\n")
    script.write("     Version {}\n".format(version))
    script.write("     Filepath Separator: \ \n")
    script.write("     Unit System: English\n")
    script.write("     Missing Flow To Zero: No\n")
    script.write("     Enable Flow Ratio: No\n")
    script.write("     Allow Blending: No\n")
    script.write("     Compute Local Flow At Junctions: No\n")
    script.write("\n")
    script.write("     Enable Sediment Routing: No\n")
    script.write("\n")
    script.write("     Enable Quality Routing: No\n")
    script.write("End:\n")
    script.write("\n")

def junctionScript(reach, reachID):
    junctions = []
    with arcpy.da.SearchCursor(reach, [reachID, "NodeID", "END_X", "END_Y", "NextDownID"]) as cursor:
        for row in cursor:
            if row[1] not in (set(junctions)):
                script.write("Junction: J-"+str(row[1])+"\n")
       	        script.write("     Canvas X: "+str(row[2])+"\n")
       	        script.write("     Canvas Y: "+str(row[3])+"\n")
       	        if row[4] in reachList:
                    script.write("     Downstream: R-"+str(row[4])+"\n")
       	        script.write("End:\n")
       	        script.write("\n")
            junctions.append(row[1])
    del row, cursor

def subbasinScript(basin, basinID):
    with arcpy.da.SearchCursor(basin, [basinID, "CENTROID_X", "CENTROID_Y", "AreaSqMI", "Imp", "CN", "NodeID", "lag_min", "lag_hrs", "initial", "suction", "conductivity", "TC_clark", "R_clark"]) as cursor:
        for row in cursor:
            script.write("Subbasin: C-"+str(row[0])+"\n")
            script.write("     Description: "+str(row[0])+"\n")
            script.write("     Canvas X: "+str(row[1])+"\n")
            script.write("     Canvas Y: "+str(row[2])+"\n")
            script.write("     Area: "+str(row[3])+"\n")
            script.write("     Downstream: J-"+str(row[6])+"\n")
            script.write("\n")

            if str(CBcn) == "true":
                script.write("     LossRate: SCS\n")
                script.write("     Percent Impervious Area: "+str(row[4])+"\n")
                script.write("     Curve Number: "+str(row[5])+"\n")
                script.write("     Initial Abstraction: "+str(initabstr)+"\n")
                script.write("\n")

            if str(CBga) == "true":
                script.write("     LossRate: Green and Ampt\n")
                script.write("     Percent Impervious Area: "+str(row[4])+"\n")
                if version == '3.5':
                    script.write("     Initial Content: "+str(row[9])+"\n")
                    script.write("     Saturated Content: "+str(satcontent)+"\n")
                elif version == '4.0':
                    script.write("     Initial Content: "+str(row[9])+"\n")
                    script.write("     Saturated Content: "+str(satcontent)+"\n")
                elif version == '4.1':
                    script.write("     Initial Content: "+str(row[9])+"\n")
                    script.write("     Saturated Content: "+str(satcontent)+"\n")
                else:
                    script.write("     Initial Loss: "+str(row[9])+"\n")
                    script.write("     Moisture Deficit: "+str(satcontent)+"\n")
                script.write("     Wetting Front Suction: "+str(row[10])+"\n")
                script.write("     Hydraulic Conductivity: "+str(row[11])+"\n")
                script.write("\n")

            if str(CBscs) == "true":
                script.write("     Transform: SCS\n")
                script.write("     Lag: "+str(row[7])+"\n")
                script.write("     Unitgraph Type: STANDARD\n")
                script.write("\n")
                script.write("     Baseflow: None\n")
                script.write("End:\n")
                script.write("\n")

            if str(CBclark) == "true":
                script.write("     Transform: Clark\n")
                script.write("     Time of Concentration: "+str(row[12])+"\n")
                script.write("     Storage Coefficient: "+str(row[13])+"\n")
                script.write("\n")
                script.write("     Baseflow: None\n")
                script.write("End:\n")
                script.write("\n")

    del row, cursor

def flowlineScript(reach, reachID):
    with arcpy.da.SearchCursor(reach, [reachID, "END_X", "END_Y", "START_X", "START_Y", "NodeID", "LENGTH_FT", "lag_min", "Slope_Fpf"]) as cursor:
        for row in cursor:
            if row[0] in reachList and row[0] not in us_subbasins:
                script.write("Reach: R-"+str(row[0])+"\n")
                script.write("     Description: Routing\n")
                script.write("     Canvas X: "+str(row[1])+"\n")
                script.write("     Canvas Y: "+str(row[2])+"\n")
                script.write("     From Canvas X: "+str(row[3])+"\n")
                script.write("     From Canvas Y: "+str(row[4])+"\n")
                script.write("     Downstream: J-"+str(row[5])+"\n")
                script.write("\n")

                if str(CBcunge) == "true":
                    script.write("     Route: Muskingum Cunge\n")
                    script.write("     Channel: "+str(shape)+"\n")
                    script.write("     Length: "+str(row[6])+"\n")
                    script.write("     Energy Slope: "+str(row[8])+"\n")
                    if shape == 'Trapezoid':
                        script.write("     Width: "+str(width)+"\n")
                        script.write("     Side Slope: "+str(sslope)+"\n")
                        script.write("     Mannings n: "+str(manning)+"\n")
                    if shape == 'Rectangular':
                        script.write("     Width: "+str(width)+"\n")
                        script.write("     Mannings n: "+str(manning)+"\n")
                    if shape == 'Triangular':
                        script.write("     Side Slope: "+str(sslope)+"\n")
                        script.write("     Mannings n: "+str(manning)+"\n")
                    if shape == '8-point':
                        script.write("     Left Overbank Mannings n: "+str(manningL)+"\n")
                        script.write("     Main Channel Mannings n: "+str(manning)+"\n")
                        script.write("     Right Overbank Mannings n: "+str(manningR)+"\n")
                    script.write("     Use Variable Time Step: No\n")
                    script.write("     Invert Elevation: "+str(invert)+"\n")
                    script.write("     Channel Loss: None\n")
                    script.write("End:\n")
                    script.write("\n")

                if str(CBlag) == "true":
                    script.write("     Route: Lag\n")
                    script.write("     Lag: "+str(row[7])+"\n")                         # Update lag (basin dictionary)
                    script.write("     Channel Loss: None\n")
                    script.write("End:\n")
                    script.write("\n")
    del row, cursor

def closeScript():
    script.write("Basin Schematic Properties:\n")
    script.write("     Last View N: 5000.0\n")
    script.write("     Last View S: -5000.0\n")
    script.write("     Last View W: -5000.0\n")
    script.write("     Last View E: 5000.0\n")
    script.write("     Maximum View N: 5000.0\n")
    script.write("     Maximum View S: -5000.0\n")
    script.write("     Maximum View W: -5000.0\n")
    script.write("     Maximum View E: 5000.0\n")
    script.write("     Extent Method: Elements\n")
    script.write("     Buffer: 0\n")
    script.write("     Draw Icons: Yes\n")
    script.write("     Draw Icon Labels: Yes\n")
    script.write("     Draw Map Objects: No\n")
    script.write("     Draw Gridlines: No\n")
    script.write("     Draw Flow Direction: No\n")
    script.write("     Fix Element Locations: No\n")
    script.write("     Fix Hydrologic Order: No\n")
    script.write("End:\n")

    script.close()


# Geometry
arcpy.AddMessage("Defining subbasin coordinates...")
basinCoords(basin)
arcpy.AddMessage("Defining subbasin area...")
basinArea(basin)
arcpy.AddMessage("Defining reach coordinates...")
reachCoords(reach)
arcpy.AddMessage("Defining reach length...")
reachLength(reach)
NextDownID(reach, reachID, FromNode, ToNode)
arcpy.AddMessage("Determining reach slope (10-85%)...")
slopeReach(reach, basin, reachID, basinID)

# Topology Lists
subbasins = []
with arcpy.da.SearchCursor(basin, [basinID]) as cursor:
    for row in cursor:
        subbasins.append(row[0])
del row, cursor

reachList = []
ds_reaches = []
with arcpy.da.SearchCursor(reach, [reachID, "NextDownID"]) as cursor:
    for row in cursor:
        reachList.append(row[0])
        ds_reaches.append(row[1])

ex_reaches = list(set(reachList) - set(subbasins))

us_subbasins = list(set(reachList) - set(ds_reaches) - set(ex_reaches))

# Topology
arcpy.AddMessage("Determining topology...")
nodeID(reach, reachID, basin, basinID, ToNode)

""" Curve Number """
arcpy.AddMessage("Determining average slope...")
basinslope(DEM, basin, basinID)
arcpy.AddMessage("Determining percent impervious...")
impervious(imperviousness, basin, basinID)
arcpy.AddMessage("Reclassiflying land use...")
reclassLU(landuse)
arcpy.AddMessage("Merging land use and soils datasets...")
unionSoilsLU(soils)
arcpy.AddMessage("Defining Curve Number lookup table...")
CNlookup()
arcpy.AddMessage("Determining individual curve number...")
indivCN(soils, soilsID)
arcpy.AddMessage("Determining composite curve number...")
compCN(basin, basinID, reduction)

""" Green Ampt """
if str(CBga) == "true":
    if initcontent and suction and conductivity:
        arcpy.AddMessage("Initializing Green & Ampt...")
        GAparams()
    else:
        arcpy.AddMessage("Determining Green & Ampt parameters...")
        GAlookup()
        domHSG(soils, basin, basinID)
        GAvalue()
else:
    GAempty()

""" Lag Time """
if str(CBcnlag) == "true":
    arcpy.AddMessage("Calculating lag time using CN Lag Method (National Engineering Handbook, Ch. 15)...")
    longestFT(basin, reachID, basinID)
    CNlag(basin, reach, timestep)

if str(CBtr55) == "true":
    arcpy.AddMessage("Calculating lag time using TR-55 method...")
    longestFT(basin, reachID, basinID)

    TR55fields(longest)
    TR55LengthEst(longest)
    TR55pts()
    TR55join(longest, longestID)

""" Clark """
if str(CBclark) == "true":
    arcpy.AddMessage("Reclassifying Land Use to Developed Land...")
    reclassDLU()
    arcpy.AddMessage("Estimating Clark parameters (DLU, DCC, DCI, DET, etc.)...")
    clarkParams()
    arcpy.AddMessage("Calculating Clark TC&R...")
    TC_R()
else:
    clarkempty()

""" Basin Script """
if str(CBtr55) == "false":
    arcpy.AddMessage("Writing results to .BASIN script file...")

    outPath = os.path.join(outFol, filename+'.BASIN')
    script = open(outPath, 'w')

    basinScript(filename)
    junctionScript(reach, reachID)
    subbasinScript(basin, basinID)
    flowlineScript(reach, reachID)
    closeScript()

if str(CBtr55) == "true":
    arcpy.AddMessage("Run TR-55 script...")

    outPath = os.path.join(outFol, filename+'.BASIN')
    script = open(outPath, 'w')

    tr55Script(filename)



























