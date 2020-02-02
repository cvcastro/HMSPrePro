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

BW = arcpy.GetParameterAsText(34)
Depth = arcpy.GetParameterAsText(35)

CBsnyder = arcpy.GetParameterAsText(36)
peaking = arcpy.GetParameterAsText(37)
steepness = arcpy.GetParameterAsText(38)

# Workspace Environment
arcpy.env.workspace = arcpy.env.scratchWorkspace = outDir
arcpy.env.overwriteOutput = True
arcpy.CheckOutExtension("spatial")
arcpy.CheckOutExtension("3D")

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

""" TR-55 Lag Time """
def TR55interpolate(DEM, longest):
    arcpy.InterpolateShape_3d(DEM, longest, "Long3D", "", "1", "BILINEAR", "DENSIFY", "0")
    arcpy.AddField_management("Long3D", "Z_us", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
    arcpy.AddField_management("Long3D", "Z_sc", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
    arcpy.AddField_management("Long3D", "Z_ch", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
    arcpy.AddField_management("Long3D", "Z_ds", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")

def TR55ptelev():
    arcpy.CalculateField_management("Long3D", "Z_us", "!shape.positionAlongLine(0,True).firstPoint.z!", "PYTHON_9.3", "")
    arcpy.CalculateField_management("Long3D", "Z_ds", "!shape.positionAlongLine(1.00,True).firstPoint.z!", "PYTHON_9.3", "")

    with arcpy.da.UpdateCursor("Long3D", ["shape@", "L_sh", "Z_sc", "L_sc", "Z_ch", "Z_us", "Z_ds"]) as cursor:
        for row in cursor:
            row[2] = round(row[0].positionAlongLine(row[1]/3.28).firstPoint.Z,2)
            row[4] = round(row[0].positionAlongLine(row[1]/3.28+row[3]/3.28).firstPoint.Z,2)
            row[5] = round(row[0].positionAlongLine(0, True).firstPoint.Z,2)
            row[6] = round(row[0].positionAlongLine(1.00, True).firstPoint.Z,2)
            cursor.updateRow(row)
    try: del row
    except: pass
    del cursor

def TR55slope():
    slope_sheet = {}
    slope_shallow = {}
    slope_channel = {}
    with arcpy.da.SearchCursor("Long3D", [longestID, "Z_us", "Z_sc", "Z_ch", "Z_ds","L_sh","L_sc","L_ch"]) as cursor:
        for row in cursor:
            slope_sheet[row[0]] = round((row[1]-row[2]) / row[5],4)
            slope_shallow[row[0]] = round((row[2]-row[3]) / row[6],4)
            slope_channel[row[0]] = round((row[3]-row[4]) / row[7],4)

    with arcpy.da.UpdateCursor("Long3D", [longestID, "S_sh", "S_sc", "S_ch"]) as cursor:
        for row in cursor:
            row[1] = slope_sheet[row[0]]
            row[2] = slope_shallow[row[0]]
            row[3] = slope_channel[row[0]]
            cursor.updateRow(row)
    try: del row
    except: pass
    del cursor

    with arcpy.da.UpdateCursor(longest, [longestID, "S_sh", "S_sc", "S_ch"]) as cursor:
        for row in cursor:
            row[1] = slope_sheet[row[0]]
            row[2] = slope_shallow[row[0]]
            row[3] = slope_channel[row[0]]
            cursor.updateRow(row)
    try: del row
    except: pass
    del cursor

    with arcpy.da.UpdateCursor(longest, [longestID, "S_sh", "S_sc", "S_ch"]) as cursor:
        for row in cursor:
            if row[1] <= 0.0001:
                row[1] = 0.0001
            if row[2] <= 0.0001:
                row[2] = 0.0001
            if row[3] <= 0.0002:
                row[3] = 0.0002
            cursor.updateRow(row)
    try: del row
    except: pass
    del cursor

def TR55lag():
    with arcpy.da.UpdateCursor(longest, ["t_sh", "n_ol", "L_sh", "Precip2yr", "S_sh"]) as cursor:
        for row in cursor:
            row[0] = 0.007 * math.pow(row[1]*row[2],0.8) / (math.pow(row[3],0.5) * math.pow(row[4],0.4))
            cursor.updateRow(row)
    del row, cursor

    with arcpy.da.UpdateCursor(longest, ["t_sc", "L_sc", "K", "S_sc"]) as cursor:
        for row in cursor:
            row[0] = row[1] / (3600 * row[2] * math.pow(row[3],0.5))
            cursor.updateRow(row)
    del row, cursor

    with arcpy.da.UpdateCursor(longest, ["t_ch", "L_ch", "n_ch", "R", "S_ch"]) as cursor:
        for row in cursor:
            row[0] = row[1] / (3600 * (1.49 / row[2]) * math.pow(row[3] , 0.66666667) * math.pow(row[4],0.5))
            cursor.updateRow(row)
    del row, cursor

    with arcpy.da.UpdateCursor(longest, ["t_c", "t_sh", "t_sc", "t_ch"]) as cursor:
        for row in cursor:
            row[0] = row[1] + row[2] + row[3]
            cursor.updateRow(row)
    del row, cursor

    with arcpy.da.UpdateCursor(longest, ["t_c"]) as cursor:
        for row in cursor:
            if row[0] <= 0.1:
                row[0] = 0.1
            cursor.updateRow(row)
    del row, cursor

    with arcpy.da.UpdateCursor(longest, ["t_c", "t_l_hrs"]) as cursor:
        for row in cursor:
            row[1] = round(row[0] * 0.6, 3)
            cursor.updateRow(row)
    del row, cursor

    with arcpy.da.UpdateCursor(longest, ["t_l_hrs", "t_l_mins"]) as cursor:
        for row in cursor:
            row[1] = round(row[0] * 60, 2)
            cursor.updateRow(row)
    del row, cursor

    TR55mins = {}
    TR55hrs = {}
    basins = []
    with arcpy.da.SearchCursor(longest, [longestID, "t_l_hrs", "t_l_mins"]) as cursor:
        for row in cursor:
            basins.append(row[0])
            TR55mins[row[0]] = row[2]
            TR55hrs[row[0]] = row[1]
    del row, cursor

    arcpy.AddField_management(basin, "lag_min", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
    arcpy.AddField_management(basin, "lag_hrs", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")

    with arcpy.da.UpdateCursor(basin, [basinID, "lag_hrs", "lag_min"]) as cursor:
        for row in cursor:
            if row[0] in basins:
                row[1] = TR55hrs[row[0]]
                row[2] = TR55mins[row[0]]
            cursor.updateRow(row)
    del row, cursor

def lag2reach():
    TR55lag_mins = {}
    with arcpy.da.SearchCursor(longest, [longestID, "t_l_mins"]) as cursor:
        for row in cursor:
            TR55lag_mins[row[0]] = row[1]
    del row, cursor

    arcpy.AddField_management(reach, "lag_min", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")

    with arcpy.da.UpdateCursor(reach, [reachID, "lag_min"]) as cursor:
        for row in cursor:
            row[1] = TR55lag_mins[row[0]]
            cursor.updateRow(row)
    del row, cursor

""" .BASIN Script """
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
    with arcpy.da.SearchCursor(basin, [basinID, "CENTROID_X", "CENTROID_Y", "AreaSqMI", "Imp", "CN", "NodeID", "lag_min", "lag_hrs", "initial", "suction", "conductivity", "TC_clark", "R_clark", "Cp","Ct","Tp"]) as cursor:
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

            if str(CBsnyder) == "true":
                script.write("     Transform: Snyder\n")
                script.write("     Snyder Method: Standard\n")
                script.write("     SnyderTp: "+str(row[16])+"\n")
                script.write("     SnyderCp: "+str(row[14])+"\n")
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

""" Lag Time """
arcpy.AddMessage("Calculating lag time using TR-55 Method...")
TR55interpolate(DEM, longest)
TR55ptelev()
TR55slope()
TR55lag()
lag2reach()

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
del row, cursor

ex_reaches = list(set(reachList) - set(subbasins))

us_subbasins = list(set(reachList) - set(ds_reaches) - set(ex_reaches))

""" Basin Script """
arcpy.AddMessage("Writing results to .BASIN script file...")

outPath = os.path.join(outFol, filename+'.BASIN')
script = open(outPath, 'w')

basinScript(filename)
junctionScript(reach, reachID)
subbasinScript(basin, basinID)
flowlineScript(reach, reachID)
closeScript()




























