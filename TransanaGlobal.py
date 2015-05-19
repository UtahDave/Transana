# Copyright (C) 2003 - 2008  The Board of Regents of the University of Wisconsin System 
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of version 2 of the GNU General Public License as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
#

"""This module contains Transana's global variables."""

__author__ = 'David Woods <dwoods@wcer.wisc.edu>, Nathaniel Case <nacase@wisc.edu>'

# Import wxPython
import wx
# import Transana's ConfigData
import ConfigData
# import Transana's Constants
import TransanaConstants
# import Python's os and sys modules
import os
import sys

# We need to know what directory the program is running from.  We use this in several
# places in the program to be able to find things like images and help files.
# This has emerged as the "preferred" cross-platform method on the wxPython-users list.
programDir = os.path.abspath(sys.path[0])
# Okay, that doesn't work with wxversion, which adds to the path.  Here's the fix, I hope.
# This should over-ride the programDir with the first value that contains Transana in the path.
for path in sys.path:
    if 'transana' in path.lower():
        programDir = path
        break
if os.path.isfile(programDir):
    programDir = os.path.dirname(programDir)


# Determine the height of the Menu Window.  
if 'wxMac' in wx.PlatformInfo:
    # We set it to 24 on the Mac!  It used to be 0, but seems to need to be 24 for wxPython 2.6.1.0.
    menuHeight = 24
elif 'wxGTK' in wx.PlatformInfo:
    # Linux, at least my FC6-Gnome setup, requires space for the Linux menu and Transana's menu.
    menuHeight = 72
else:
    # While we default to 44, this value actually can get altered elsewhere to reflect the height of
    # the title/header bar.  XP using Large Fonts, for example, needs a larger value.
    menuHeight = 44

# Menu Window, defined in Transana.py
menuWindow = None
# Chat Window, defined in Transana.py
chatWindow = None
# define the primary Socket Connection
socketConnection = None

# Prepare the wxPrintData object for use in Printing
printData = wx.PrintData()
# wxPython defaults to A4 paper.  Transana should default to Letter
printData.SetPaperId(wx.PAPER_LETTER)

# Declare the default character encoding for Transana.  This MUST be declared before the ConfigData call.
# Furthermore, it must ignore the possibility of Russian or other languages for now, as the
# configData.language setting is not yet known.
if ('wxMSW' in wx.PlatformInfo) and (TransanaConstants.singleUserVersion):
    encoding = 'latin1'
else:
    encoding = 'utf8'

# We need to know the MySQL version to know if UTF-8 is supported.  Initialize that here.
DBVersion = 0

# Create a Configuration Data Object.  This automatically load previously saved configuration information
configData = ConfigData.ConfigData()

# Now that we've loaded the Configuration Data, we can see if we need to alter the default encoding
# If we're on Windows, single-user, using Russian, use KOI8r encoding instead of Latin-1,
# Chinese uses big5, Japanese uses cp932, and Korean uses cp949
if ('wxMSW' in wx.PlatformInfo) and (TransanaConstants.singleUserVersion):
    if (configData.language == 'ru'):
        encoding = 'koi8_r'
    elif (configData.language == 'zh'):
        encoding = TransanaConstants.chineseEncoding
    elif (configData.language == 'el'):
        encoding = 'iso8859_7'
    elif (configData.language == 'ja'):
        encoding = 'cp932'
    elif (configData.language == 'ko'):
        encoding = 'cp949'

# Create a variable for the global User Name information
userName = ''

# We need to know the maximum length of the Keyword Group field in a couple of places
maxKWGLength = 50

# Adding user color configuration has made working with color more complicated, so we need to move it from
# TransanaConstants to TransanaGlobal.

# We need a function for getting color definitions loaded.  
def getColorDefs(filename):
    """ Load Color Definitions file """
    # If a filename was passed in and points to a file that exists ...
    if (filename != '') and (os.path.exists(filename)):
        # Initialize the color list
        colorList = []
        # Start exception handling
        try:
            # Open the file to be read
            f = file(filename, 'r')
            # Initialize the line counter
            lineCount = 1
            # Read each line in the file
            for line in f:
                # When we run out of lines, stop processing them!
                if not line:
                    break
                # If the line is not a comment and is not blank ...
                if (line[0] != '#') and (line.strip() != ''):
                    # Divide the line up into its component values
                    (colName, redVal, greenVal, blueVal) = line.strip().split(',')
                    # Convert R, G, and B into integers for error checking (raises ValueError if conversion fails)
                    redVal = int(redVal)
                    greenVal = int(greenVal)
                    blueVal = int(blueVal)
                    # If the color is not named, or has a value outside of 0 - 255 ...
                    if (colName == '') or \
                       (blueVal < 0) or (blueVal > 255) or \
                       (greenVal < 0) or (greenVal > 255) or \
                       (redVal < 0) or (redVal > 255):
                        # ... use a ValueError exception to signal the problem
                        raise ValueError
                    colorList.append((colName, (redVal, greenVal, blueVal)))
                # increment the line counter
                lineCount += 1
        # If an exception is raised ...
        except:
            # ... Create an error message
            msg = _('Error reading configuration file "%s" at line %d.') + "\n\n%s"
            # NOTE:  msg is already Unicode at this point, so no need to convert it!  Note sure why.  Default Encoding not yet changed??
            if (type(msg) != unicode) and ('unicode' in wx.PlatformInfo):
                msg = unicode(msg, 'utf8')
            # No wxApp has been created yet.  We can't display an error message unless we create one here!
            tmpApp = wx.App()
            # Display an error message.  We can't use Trasnana's ErrorDialog yet.
            dlg = wx.MessageDialog(None, msg % (filename, lineCount, line), _("Transana Error"), wx.OK | wx.CENTRE | wx.ICON_ERROR)
            dlg.ShowModal()
            dlg.Destroy()
            # Add White to the end of the list (as much as was read in, anyway) so that this element is on the end.
            colorList.append(('White',             (255, 255, 255)))
            # Destroy the temporary wxApp object we created.
            tmpApp.Destroy()
    # If we don't have a Color Definition file to load ...
    else:
        # We want enough colors, but not too many.  This list seems about right to me.  I doubt my color names are standard.
        # But then, I'm often perplexed by the colors that are included and excluded by most programs.  (Excel for example.)
        # Each entry is made up of a color name and a tuple of the RGB values for the color.
        colorList = [('Dark Blue',         (  0,   0, 128)),
                     ('Blue',              (  0,   0, 255)),
                     ('Light Blue',        (  0, 128, 255)),
                     ('Lavender',          (128, 128, 255)),
                     ('Cyan',              (  0, 255, 255)),
                     ('Blue Green',        (  0, 128, 128)),
                     ('Dark Slate Gray',   ( 47,  79,  79)),
                     ('Dark Green',        (  0, 128,   0)),
                     ('Green Blue',        (  0, 255, 128)),
                     ('Chartreuse',        (128, 255,   0)),
                     ('Olive',             (128, 128,   0)),
                     ('Sienna',            (142, 107,  35)),
                     ('Gray',              (128, 128, 128)),
                     ('Purple',            (128,   0, 255)),
                     ('Light Purple',      (176,  0, 255)),
                     ('Dark Purple',       (128,   0, 128)),
                     ('Maroon',            (128,   0,   0)),
                     ('Indian Red',        ( 79,  47,  47)),
                     ('Violet Red',        (204,  50, 153)),
                     ('Magenta',           (255,   0, 255)),
                     ('Light Fuscia',      (255, 128, 255)),
                     ('Rose',              (255,   0, 128)),
                     ('Red',               (255,   0,   0)),
                     ('Red Orange',        (204,  50,  50)),
                     ('Salmon',            (255, 128, 128)),
                     ('Orange',            (255, 128,   0)),
                     ('Yellow',            (255, 255,   0)),  
                     ('Goldenrod',         (219, 219, 112)),
                     ('White',             (255, 255, 255))]
        # Signal the config data that we didn't load a file
        configData.colorConfigFilename = ''
    # Return the list of colors we've loaded
    return colorList

# Get our initial GRAPHICS color definitions
transana_graphicsColorList = getColorDefs(configData.colorConfigFilename)
# We want enough colors for TEXT, but not too many.  This list seems about right to me.  I doubt my color names are standard.
# But then, I'm often perplexed by the colors that are included and excluded by most programs.  (Excel for example.)
# Each entry is made up of a color name and a tuple of the RGB values for the color.
transana_textColorList = [('Black',             (  0,   0,   0)),
                          ('Dark Blue',         (  0,   0, 128)),
                          ('Blue',              (  0,   0, 255)),
                          ('Light Blue',        (  0, 128, 255)),
                          ('Lavender',          (128, 128, 255)),
                          ('Cyan',              (  0, 255, 255)),
                          ('Light Aqua',        (128, 255, 255)),
                          ('Blue Green',        (  0, 128, 128)),
                          ('Dark Slate Gray',   ( 47,  79,  79)),
                          ('Dark Green',        (  0, 128,   0)),
                          ('Green Blue',        (  0, 255, 128)),
                          ('Green',             (  0, 255,   0)),
                          ('Chartreuse',        (128, 255,   0)),
                          ('Light Green',       (128, 255, 128)),
                          ('Olive',             (128, 128,   0)),
                          ('Sienna',            (142, 107,  35)),
                          ('Gray',               (128, 128, 128)),
                          ('Purple',            (128,   0, 255)),
                          ('Light Purple',      (176,  0, 255)),
                          ('Dark Purple',       (128,   0, 128)),
                          ('Maroon',            (128,   0,   0)),
                          ('Indian Red',        ( 79,  47,  47)),
                          ('Violet Red',        (204,  50, 153)),
                          ('Magenta',           (255,   0, 255)),
                          ('Light Fuscia',      (255, 128, 255)),
                          ('Rose',              (255,   0, 128)),
                          ('Red',               (255,   0,   0)),
                          ('Red Orange',        (204,  50,  50)),
                          ('Salmon',            (255, 128, 128)),
                          ('Orange',            (255, 128,   0)),
                          ('Yellow',            (255, 255,   0)),  
                          ('Light Yellow',      (255, 255, 128)),  
                          ('Goldenrod',         (219, 219, 112)),
                          ('White',             (255, 255, 255))]

# Once we have a set of colors defined, we need several data structures that allow us to work with these colors.
# To make changing colors easier, this process was made into a function.
def SetColorVariables():
    """ Set up variables for working with colors """
    # It helps to have a list of the names of legal TEXT colors for the Font Dialog
    transana_colorNameList = []
    # Iterate through the Text Colors and grab their names
    for (colorName, colorDef) in transana_textColorList:
        transana_colorNameList.append(colorName)
    # We sometimes need to look a GRAPHICS color up by its name
    transana_colorLookup = {}
    # Iterate through the list of Graphics colors and build a dictionary for looking up color definition based on name
    for (colorName, colorDef) in transana_graphicsColorList:
        transana_colorLookup[colorName] = colorDef
    # Get the legal colors for bars in the Keyword Map.  These colors are taken from the TransanaGlobal.transana_graphicsColorList
    # but are put in a different order for the Keyword Map.
    keywordMapColourSet = []
    for x in range(10):
        for y in range(0, len(transana_graphicsColorList) - 1, 10):
            if x + y < len(transana_graphicsColorList) - 1:
                keywordMapColourSet.append(transana_graphicsColorList[x + y][0])
    return (transana_colorNameList, transana_colorLookup, keywordMapColourSet)

# Get key color manipulation data structures from our ColorVariables function
(transana_colorNameList, transana_colorLookup, keywordMapColourSet) = SetColorVariables()

# The following exists only to ensure that the color names are available for translation.
# (I had to take the translation code out of the color definition data structure, as color names were only showing up in
#  the initial language.) This is needed for Text Colors, not for Graphics Colors, and is displayed in the Font Dialog.
tmpColorList = (_('Black'), _('Dark Blue'), _('Blue'), _('Light Blue'), _('Cyan'), _('Light Aqua'), _('Green Blue'),
                 _('Dark Green'), _('Blue Green'),_('Green'), _('Chartreuse'), _('Light Green'), _('Olive'), _('Gray'),
                _('Lavender'), _('Purple'), _('Dark Purple'), _('Maroon'), _('Magenta'), _('Light Fuscia'), _('Rose'),
                _('Red'), _('Salmon'), _('Orange'), _('Yellow'), _('Light Yellow'), _('White'),
                _('Violet Red'), _('Sienna'), _('Indian Red'), _('Goldenrod'), _('Dark Slate Gray'), _('Red Orange'),
                _('Light Purple'))

# We want enough shades of gray for black and white GRAPHICS printing, but not too many.  This list seems about right to me.
# Each entry is made up of a color name and a tuple of the RGB values for the color.
transana_grayList = [('Black',             (  0,   0,   0)),
                     ('Dark Gray',         ( 79,  79,  79)),
                     ('Gray',              (158, 158, 158)),
                     ('Light Gray',        (237, 237, 237)),
                     ('White',             (255, 255, 255))]

# Get the legal shades of gray for bars in the Keyword Map.  These shades are taken from the TransanaGlobal.transana_grayList
keywordMapGraySet = ['Black',
                     'Gray',
                     'Dark Gray',
                     'Light Gray']
# We sometimes need to look a GRAPHICS color up by its name
transana_grayLookup = {}
# Iterate through the list of Graphics "Black and White" colors and build a dictionary for looking up color definition based on name
for (colorName, colorDef) in transana_grayList:
    transana_grayLookup[colorName] = colorDef