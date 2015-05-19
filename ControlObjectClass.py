# Copyright (C) 2003 - 2008 The Board of Regents of the University of Wisconsin System 
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

"""This module implements the Control Object class for Transana,
which is responsible for managing communication between the
four main windows.  Each object (Menu, Visualization, Video, Transcript,
and Data) should communicate only with the Control Object, not with
each other.
"""

__author__ = 'David Woods <dwoods@wcer.wisc.edu>, Rajas Sambhare'

DEBUG = False
if DEBUG:
    print "ControlObjectClass DEBUG is ON!"

# Import wxPython
import wx

# import Transana's Constants
import TransanaConstants
# Import the Menu Constants
import MenuSetup
# Import Transana's Global Values
import TransanaGlobal
# import the Transana Series Object definition
import Series
# import the Transana Episode Object definition
import Episode
# import the Transana Transcript Object definition
import Transcript
# import the Transana Collection Object definition
import Collection
# import the Transana Clip Object definition
import Clip
# import the Transana Miscellaneous Routines
import Misc
# import Transana Database Interface
import DBInterface
# import Transana's Dialogs
import Dialogs
# import Transana's DragAndDrop Objects for Quick Clip creation
import DragAndDropObjects
# import Transana File Management System
import FileManagement
# import the Episode Transcript Change Propagation tool
import PropagateEpisodeChanges
# import Transana's Exceptions
import TransanaExceptions
# Import Transana's Transcript User Interface for creating supplemental Transcript Windows
import TranscriptionUI

# import Python's os module
import os
# import Python's sys module
import sys
# import Python's pickle module
import pickle


class ControlObject(object):
    """ The ControlObject operationalizes all inter-window and inter-object communication and control.
        All objects should speak only to the ControlObject, not to each other directly.  The purpose of
        this is to allow greater modularity of code, so that modules can be swapped in and out in with
        changes affecting only this object if the APIs change.  """
    def __init__(self):
        """ Initialize the ControlObject """
        # Define Objects that need controlling (initializing to None)
        self.MenuWindow = None
        self.VideoWindow = None
        # There may be multiple Transcript Windows.  We'll use a List to keep track of them.
        self.TranscriptWindow = []
        # We need to know what transcript is "Active" (most recently selected) at any given point.  -1 signals none.
        self.activeTranscript = -1
        self.VisualizationWindow = None
        self.DataWindow = None
        self.PlayAllClipsWindow = None
        self.NotesBrowserWindow = None
        self.ChatWindow = None

        # Initialize variables
        self.VideoFilename = ''         # Video File Name
        self.VideoStartPoint = 0        # Starting Point for video playback in Milliseconds
        self.VideoEndPoint = 0          # Ending Point for video playback in Milliseconds
        self.WindowPositions = []       # Initial Screen Positions for all Windows, used for Presentation Mode
        self.TranscriptNum = []         # Transcript record # LIST loaded
        self.currentObj = None          # Currently loaded Object (Episode or Clip)
        self.shuttingDown = False       # We need to signal when we want to shut down to prevent problems
                                        # with the Visualization Window's IDLE event trying to call the
                                        # VideoWindow after it's been destroyed.
        
    def Register(self, Menu='', Video='', Transcript='', Data='', Visualization='', PlayAllClips='', NotesBrowser='', Chat=''):
        """ The ControlObject can extert control only over those objects it knows about.  This method
            provides a way to let the ControlObject know about other objects.  This infrastructure allows
            for objects to be swapped in and out.  For example, if you need a different video window
            that supports a format not available on the current one, you can hide the current one, show
            a new one, and register that new one with the ControlObject.  Once this is done, the new
            player will handle all tasks for the program.  """
        # This function expects parameters passed by name and "registers" the components that
        # need to be available to the ControlObject to be controlled.  To remove an
        # object registration, pass in "None"
        if Menu != '':
            self.MenuWindow = Menu                       # Define the Menu Window Object
        if Video != '':
            self.VideoWindow = Video                     # Define the Video Window Object
        if Transcript != '':
            # Add the Transcript Window reference to the list of Transcript Windows
            self.TranscriptWindow.append(Transcript)
            # Add the Transcript Number to the list of Transcript Numbers
            self.TranscriptNum.append(0)
            # Set the new Transcript to be the Active Transcript
            self.activeTranscript = len(self.TranscriptWindow) - 1
        if Data != '':
            self.DataWindow = Data                       # Define the Data Window Object
        if Visualization != '':
            self.VisualizationWindow = Visualization     # Define the Visualization Window Object
        if PlayAllClips != '':
            self.PlayAllClipsWindow = PlayAllClips       # Define the Play All Clips Window Object
        if NotesBrowser != '':
            self.NotesBrowserWindow = NotesBrowser             # Define the Notes Browser Window Object
        if Chat != '':
            self.ChatWindow = Chat                       # Define the Chat Window Object

    def CloseAll(self):
        """ This method closes all application windows and cleans up objects when the user
            quits Transana. """
        # Closing the MenuWindow will automatically close the Transcript, Data, and Visualization
        # Windows in the current setup of Transana, as these windows are all defined as child dialogs
        # of the MenuWindow.
        self.MenuWindow.Close()
        # VideoWindow is a wxFrame, rather than a wxDialog like the other windows.  Therefore,
        # it needs to be closed explicitly.
        self.VideoWindow.close()

    def LoadTranscript(self, series, episode, transcript):
        """ When a Transcript is identified to trigger systemic loading of all related information,
            this method should be called so that all Transana Objects are set appropriately. """
        # Before we do anything else, let's save the current transcript if it's been modified.
        if self.TranscriptWindow[self.activeTranscript].TranscriptModified():
            self.SaveTranscript(1, cleardoc=1)
        # activeTranscript 0 signals we should reset everything in the interface!
        if self.activeTranscript == 0:
            clearAll = True
        else:
            clearAll = False
        # Clear all Windows
        self.ClearAllWindows(resetMultipleTranscripts = clearAll)
        # Because transcript names can be identical for different episodes in different series, all parameters are mandatory.
        # They are:
        #   series      -  the Series associated with the desired Transcript
        #   episode     -  the Episode associated with the desired Transcript
        #   transcript  -  the Transcript to be displayed in the Transcript Window
        seriesObj = Series.Series(series)                                    # Load the Series which owns the Episode which owns the Transcript
        episodeObj = Episode.Episode(series=seriesObj.id, episode=episode)   # Load the Episode in the Series that owns the Transcript
        # Set the current object to the loaded Episode
        self.currentObj = episodeObj
        transcriptObj = Transcript.Transcript(transcript, ep=episodeObj.number)

        # Load the Transcript in the Episode in the Series
        # reset the video start and end points
        self.VideoStartPoint = 0                                     # Set the Video Start Point to the beginning of the video
        self.VideoEndPoint = 0                                       # Set the Video End Point to 0, indicating that the video should not end prematurely
        
        # Remove any tabs in the Data Window beyond the Database Tab
        self.DataWindow.DeleteTabs()

        if self.LoadVideo(episodeObj.media_filename, 0, episodeObj.tape_length):    # Load the video identified in the Episode
            # Delineate the appropriate start and end points for Video Control.  (Required to prevent Waveform Visualization problems)
            self.SetVideoSelection(0, 0)

            # Force the Visualization to load here.  This ensures that the Episode visualization is shown
            # rather than the Clip visualization when Locating a Clip
            self.VisualizationWindow.OnIdle(None)
            
            # Identify the loaded Object
            prompt = _('Transcript "%s" for Series "%s", Episode "%s"')
            if self.activeTranscript > 0:
                prompt = '** ' + prompt + ' **'
            if 'unicode' in wx.PlatformInfo:
                # Encode with UTF-8 rather than TransanaGlobal.encoding because this is a prompt, not DB Data.
                prompt = unicode(prompt, 'utf8')
            # Set the window's prompt
            self.TranscriptWindow[self.activeTranscript].dlg.SetTitle(prompt % (transcriptObj.id, seriesObj.id, episodeObj.id))
            # Identify the loaded media file
            if 'unicode' in wx.PlatformInfo:
                # Encode with UTF-8 rather than TransanaGlobal.encoding because this is a prompt, not DB Data.
                prompt = unicode(_('Video Media File: "%s"'), 'utf8')
            else:
                prompt = _('Video Media File: "%s"')
            self.VideoWindow.frame.SetTitle(prompt % episodeObj.media_filename)
            # Open Transcript in Transcript Window
            self.TranscriptWindow[self.activeTranscript].LoadTranscript(transcriptObj) #flies off to transcriptionui.py
            # Add the Transcript Number to the list that tracks the numbers of the open transcripts
            self.TranscriptNum[self.activeTranscript] = transcriptObj.number
            
            # Add the Episode Clips Tab to the DataWindow
            self.DataWindow.AddEpisodeClipsTab(seriesObj=seriesObj, episodeObj=episodeObj)

            # Add the Selected Episode Clips Tab, initially set to the beginning of the video file
            # TODO:  When the Transcript Window updates the selected text, we need to update this tab in the Data Window!
            self.DataWindow.AddSelectedEpisodeClipsTab(seriesObj=seriesObj, episodeObj=episodeObj, TimeCode=0)

            # Add the Keyword Tab to the DataWindow
            self.DataWindow.AddKeywordsTab(seriesObj=seriesObj, episodeObj=episodeObj)
            # Enable the transcript menu item options
            self.MenuWindow.SetTranscriptOptions(True)

            # When an Episode is first loaded, we don't know how long it is.  
            # Deal with missing episode length.
            if episodeObj.tape_length <= 0:
                # The video has been loaded in the Media Player now, so this should work.
                episodeObj.tape_length = self.GetMediaLength()
                # If we now know the Media Length...
                if episodeObj.tape_length > 0:
                    # Let's try to save the Episode Object, since we've added information
                    try:
                        episodeObj.lock_record()
                        episodeObj.db_save()
                        episodeObj.unlock_record()
                    except:
                        pass

        else:
            # We only want to load the File Manager in the Single User version.  It's not the appropriate action
            # for the multi-user version!
            if TransanaConstants.singleUserVersion:
                # Create a File Management Window
                fileManager = FileManagement.FileManagement(self.MenuWindow, -1, _("Transana File Management"))
                # Set up, display, and process the File Management Window
                fileManager.Setup(showModal=True)
                # Destroy the File Manager window
                fileManager.Destroy()

    def LoadClipByNumber(self, clipNum):
        """ When a Clip is identified to trigger systematic loading of all related information,
            this method should be called so that all Transana Objects are set appropriately. """
        # Before we do anything else, let's save the current transcript if it's been modified.
        if self.TranscriptWindow[self.activeTranscript].TranscriptModified():
            self.SaveTranscript(1, cleardoc=1)
        # Set Active Transcript to 0 to signal close of all existing secondary Transcript Windows
        self.activeTranscript = 0
        # Clear all Windows
        self.ClearAllWindows()
        # Load the Clip based on the ClipNumber
        clipObj = Clip.Clip(clipNum)
        # Set the current object to the loaded Episode
        self.currentObj = clipObj
        # Load the Collection that contains the loaded Clip
        collectionObj = Collection.Collection(clipObj.collection_num)
        # set the video start and end points to the start and stop points defined in the clip
        self.VideoStartPoint = clipObj.clip_start                     # Set the Video Start Point to the Clip beginning
        self.VideoEndPoint = clipObj.clip_stop                        # Set the Video End Point to the Clip end
        
        # Load the video identified in the Clip
        if self.LoadVideo(clipObj.media_filename, clipObj.clip_start, clipObj.clip_stop - clipObj.clip_start):
            # Identify the loaded media file
            if 'unicode' in wx.PlatformInfo:
                # Encode with UTF-8 rather than TransanaGlobal.encoding because this is a prompt, not DB Data.
                str = unicode(_('Video Media File: "%s"'), 'utf8')
            else:
                str = _('Video Media File: "%s"')
            self.VideoWindow.frame.SetTitle(str % clipObj.media_filename)
            # Delineate the appropriate start and end points for Video Control
            self.SetVideoSelection(self.VideoStartPoint, self.VideoEndPoint)
            # Identify the loaded Object
            if 'unicode' in wx.PlatformInfo:
                # Encode with UTF-8 rather than TransanaGlobal.encoding because this is a prompt, not DB Data.
                str = unicode(_('Transcript for Collection "%s", Clip "%s"'), 'utf8') % (collectionObj.GetNodeString(), clipObj.id)
            else:
                str = _('Transcript for Collection "%s", Clip "%s"') % (collectionObj.GetNodeString(), clipObj.id)
            # The Mac doesn't clean up around frame titles!
            # (The Mac centers titles, while Windows left-justifies them and should not get the leading spaces!)
            if 'wxMac' in wx.PlatformInfo:
                str = "               " + str + "               "
            self.TranscriptWindow[self.activeTranscript].dlg.SetTitle(str)
            # Open the first Clip Transcript in Transcript Window (activeTranscript is ALWAYS 0 here!)
            self.TranscriptWindow[self.activeTranscript].LoadTranscript(clipObj.transcripts[0])
            # Open the remaining clip transcripts in additional transcript windows.
            for tr in clipObj.transcripts[1:]:
                self.OpenAdditionalTranscript(tr.number, isEpisodeTranscript=False)
                self.TranscriptWindow[len(self.TranscriptWindow) - 1].dlg.SetTitle(str)

            # Remove any tabs in the Data Window beyond the Database Tab.  (This was moved down to late in the
            # process due to problems on the Mac documented in the DataWindow object.)
            self.DataWindow.DeleteTabs()

            # Add the Keyword Tab to the DataWindow
            self.DataWindow.AddKeywordsTab(collectionObj=collectionObj, clipObj=clipObj)

            # Let's make sure this clip is displayed in the Database Tree
            nodeList = (_('Collections'),) + self.currentObj.GetNodeData()
            # Now point the DBTree (the notebook's parent window's DBTab's tree) to the loaded Clip
            self.DataWindow.DBTab.tree.select_Node(nodeList, 'ClipNode')
            
            # Enable the transcript menu item options
            self.MenuWindow.SetTranscriptOptions(True)

            return True
        else:
            # Remove any tabs in the Data Window beyond the Database Tab
            self.DataWindow.DeleteTabs()

            # We only want to load the File Manager in the Single User version.  It's not the appropriate action
            # for the multi-user version!
            if TransanaConstants.singleUserVersion:
                # Create a File Management Window
                fileManager = FileManagement.FileManagement(self.MenuWindow, -1, _("Transana File Management"))
                # Set up, display, and process the File Management Window
                fileManager.Setup(showModal=True)
                # Destroy the File Manager window
                fileManager.Destroy()

            return False

    def OpenAdditionalTranscript(self, transcriptNum, seriesID='', episodeID='', isEpisodeTranscript=True):
        """ Open an additional Transcript without replacing the current one """
        # Create a new Transcript Window
        newTranscriptWindow = TranscriptionUI.TranscriptionUI(TransanaGlobal.menuWindow, includeClose=True)
        # Register this new Transcript Window with the Control Object (self)
        self.Register(Transcript=newTranscriptWindow)
        # Register the Control Object (self) with the new Transcript Window
        newTranscriptWindow.Register(self)
        # Get out Transcript object from the database
        transcriptObj = Transcript.Transcript(transcriptNum)
        # If we have an Episode Transcript, it needs a Window title.  (Clip titles are handled in the calling routine.)
        if isEpisodeTranscript:
            # If we haven't been sent an Episode ID ...
            if episodeID == '':
                # ... get the Episode data based on the Transcript Object ...
                episodeObj = Episode.Episode(transcriptObj.episode_num)
                # ... and note the Episode ID
                episodeID = episodeObj.id
            # If we haven't been sent the Series ID ...
            if seriesID == '':
                # ... get the Series data based on the Episode object ...
                seriesObj = Series.Series(episodeObj.series_num)
                # ... and note the Series ID
                seriesID = seriesObj.id
            # Identify the loaded Object
            prompt = _('Transcript "%s" for Series "%s", Episode "%s"')
            if self.activeTranscript > 0:
                prompt = '** ' + prompt + ' **'
            if 'unicode' in wx.PlatformInfo:
                # Encode with UTF-8 rather than TransanaGlobal.encoding because this is a prompt, not DB Data.
                prompt = unicode(prompt, 'utf8')
            # Set the window's prompt
            newTranscriptWindow.dlg.SetTitle(prompt % (transcriptObj.id, seriesID, episodeID))
        # Load the transcript text into the new transcript window
        newTranscriptWindow.LoadTranscript(transcriptObj)
        # Add the new transcript's number to the list that tracks the numbers of the open transcripts.
        self.TranscriptNum[self.activeTranscript] = transcriptObj.number

        # Now we need to arrange the various Transcript windows.
        # if Auto Arrange is enabled ...
        if TransanaGlobal.configData.autoArrange:
            self.AutoArrangeTranscriptWindows()
        # If Auto Arrange is OFF
        else:
            # Determine the position and size of the LAST Transcript Window
            (left, top) = self.TranscriptWindow[self.activeTranscript - 1].dlg.GetPositionTuple()
            (width, height) = self.TranscriptWindow[self.activeTranscript - 1].dlg.GetSizeTuple()
            # Make the new Transcript offset from the last transcript and just a little smaller
            self.TranscriptWindow[self.activeTranscript].dlg.SetDimensions(left + 16, top + 16, width - 16, height - 16)
        # Display the new Transcript window
        newTranscriptWindow.Show()
        newTranscriptWindow.UpdatePosition(self.VideoWindow.GetCurrentVideoPosition())

        if DEBUG:
            print "ControlObjectClass.OpenAdditionalTranscript(%d)  %d" % (transcriptNum, self.activeTranscript)
            for x in range(len(self.TranscriptWindow)):
                print x, self.TranscriptWindow[x].transcriptWindowNumber, self.TranscriptNum[x]
            print
        
    def CloseAdditionalTranscript(self, transcriptNum):
        """ Close a secondary transcript """
        # If we're closeing a transcript other than the active transscript ...
        if self.activeTranscript != transcriptNum:
            # ... remember which transcript WAS active ...
            prevActiveTranscript = self.activeTranscript
            # ... and make the one we're supposed to close active.
            self.activeTranscript = transcriptNum
        # If we're closing the active transcript ...
        else:
            # ... then focus should switch to the top transcript, # 0
            prevActiveTranscript = 0
        # If the prevActiveTranscript is about to be closed, we need to reduce it by one to avoid
        # problems on the Mac.
        if prevActiveTranscript == len(self.TranscriptWindow) - 1:
            prevActiveTranscript = self.activeTranscript - 1
        # Before we do anything else, let's save the current transcript if it's been modified.
        if self.TranscriptWindow[transcriptNum].TranscriptModified():
            self.SaveTranscript(1, cleardoc=1)
        if transcriptNum == 0:
            (left, top) = self.TranscriptWindow[0].dlg.GetPositionTuple()
            self.TranscriptWindow[1].dlg.SetPosition(wx.Point(left, top))
        # ... remove it from the Transcript Window list
        del(self.TranscriptWindow[transcriptNum])
        # ... and remove it from the Transcript Numbers list
        del(self.TranscriptNum[transcriptNum])
        # When all the Transcript Windows are closed, rearrrange the screen
        self.AutoArrangeTranscriptWindows()
        # We need to update the window numbers of the transcript windows.
        for x in range(len(self.TranscriptWindow)):
            # Update the TranscriptUI object
            self.TranscriptWindow[x].transcriptWindowNumber = x
            # Also update the TranscriptUI's Dialog object.  (This is crucial)
            self.TranscriptWindow[x].dlg.transcriptWindowNumber = x
        # Set the frame focus to the Previous active transcript (I'm not convinced this does anything!)
        self.TranscriptWindow[prevActiveTranscript].dlg.SetFocus()
        # Update the Active Transcript number
        self.activeTranscript = prevActiveTranscript

    def SaveAllTranscriptCursors(self):
        """ Save the current cursor position or selection for all open Transcript windows """
        # For each Transcript Window ...
        for trWin in self.TranscriptWindow:
            # ... save the cursorPosition
            trWin.dlg.editor.SaveCursor()

    def RestoreAllTranscriptCursors(self):
        """ Restore the previously saved cursor position or selection for all open Transcript windows """
        # For each Transcript Window ...
        for trWin in self.TranscriptWindow:
            # ... if it HAS a saved cursorPosition ...
            if trWin.dlg.editor.cursorPosition != 0:
                # ... restore the cursor position or selection
                trWin.dlg.editor.RestoreCursor()

    def AutoArrangeTranscriptWindows(self):
        # If we have more than one window ...
        if len(self.TranscriptWindow) > 1:
            # ... define a style that includes the Close Box.  (System_Menu is required for Close to show on Windows in wxPython.)
            style = wx.CAPTION | wx.RESIZE_BORDER | wx.WANTS_CHARS | wx.SYSTEM_MENU | wx.CLOSE_BOX
        # If there's only one window...
        else:
            # ... then we don't want the close box
            style = wx.CAPTION | wx.RESIZE_BORDER | wx.WANTS_CHARS
        # Reset the style for the top window
        self.TranscriptWindow[0].dlg.SetWindowStyleFlag(style)
        # Some style changes require a refresh
        self.TranscriptWindow[0].dlg.Refresh()
        # Determine the position and size of the first Transcript
        (left, top) = self.TranscriptWindow[0].dlg.GetPositionTuple()
        (width, height) = self.TranscriptWindow[0].dlg.GetSizeTuple()
        # Get the size of the full screen
        (x, y, w, h) = wx.ClientDisplayRect()
        # We don't want the height of the first Transcript window, but the size of the space for all Transcript windows.
        # We assume that it extends from the top of the first Transcript window to the bottom of the whole screen.
        height = h - top
        # We need an adjustment for the Mac.  I don't know why exactly.  It might have to do with the height of the menu bar.
        if 'wxMac' in wx.PlatformInfo:
            height += 20
        # And actually, the width may very well be incorrect.  Let's grab the width from the Visualization Window
        (width, vh) = self.VisualizationWindow.GetSizeTuple()
        # Initialize a Window Counter
        cnt = 0
        # Iterate through all the Transcript Windows
        for win in self.TranscriptWindow:
            # Increment the counter
            cnt += 1
            # Set the position of each window so they evenly fill up the Transcript space
            win.dlg.SetDimensions(left, top + int((cnt-1) * (height / len(self.TranscriptWindow))), width, int(height / len(self.TranscriptWindow)))

    def ClearAllWindows(self, resetMultipleTranscripts = True):
        """ Clears all windows and resets all objects """
        # Prompt for save if transcript modifications exist
        self.SaveTranscript(1)
        if resetMultipleTranscripts:
            self.activeTranscript = 0
        # Reset the ControlObject's TranscriptNum
        self.TranscriptNum[self.activeTranscript] = 0
        # Clear Transcript Window
        self.TranscriptWindow[self.activeTranscript].ClearDoc()
        # Identify the loaded Object
        str = _('Transcript')
        self.TranscriptWindow[self.activeTranscript].dlg.SetTitle(str)

        # If the Active Transcript is set to 0, that signals the load of a NEW video
        if resetMultipleTranscripts:

            # Clear the Menu Window (Reset menus to initial state)
            self.MenuWindow.ClearMenus()
            # Clear Visualization Window
            self.VisualizationWindow.ClearVisualization()
            # Clear the Video Window
            self.VideoWindow.ClearVideo()
            # Clear the Video Filename as well!
            self.VideoFilename = ''
            # Identify the loaded media file
            str = _('Video')
            self.VideoWindow.frame.SetTitle(str)
            
            # While there are additional Transcript windows open ...
            while len(self.TranscriptWindow) > 1:
                # Save the transcript
                self.SaveTranscript(1, transcriptToSave=len(self.TranscriptWindow) - 1)

                # Clear Transcript Window
                self.TranscriptWindow[len(self.TranscriptWindow) - 1].ClearDoc()
                self.TranscriptWindow[len(self.TranscriptWindow) - 1].dlg.Close()
#            self.activeTranscript = 0
            # When all the Transcritp Windows are closed, rearrrange the screen
            self.AutoArrangeTranscriptWindows()
                
            # Clear the Data Window
            self.DataWindow.ClearData()
            # Clear the currently loaded object, as there is none
            self.currentObj = None
            # Force the screen updates
            
        # there can be an issue with recursive calls to wxYield, so trap the exception ...
        try:
            wx.Yield()
        # ... and ignore it!
        except:
            pass

    def GetNewDatabase(self):
        """ Close the old database and open a new one. """
        # set the active transcript to 0 so multiple transcript will be cleared
        self.activeTranscript = 0
        # Clear all existing Data
        self.ClearAllWindows()
        # If we're in multi-user ...
        if not TransanaConstants.singleUserVersion:
            # ... stop the Connection Timer so it won't fire while the Database is closed
            TransanaGlobal.connectionTimer.Stop()
        # Close the existing database connection
        DBInterface.close_db()
        # Reset the global encoding to UTF-8 if the Database supports it
        if TransanaGlobal.DBVersion >= u'4.1':
            TransanaGlobal.encoding = 'utf8'
        # Otherwise, if we're in Russian, change the encoding to KOI8r
        elif TransanaGlobal.configData.language == 'ru':
            TransanaGlobal.encoding = 'koi8_r'
        # If we're in Chinese, change the encoding to the appropriate Chinese encoding
        elif TransanaGlobal.configData.language == 'zh':
            TransanaGlobal.encoding = TransanaConstants.chineseEncoding
        # If we're in East Europe Encoding, change the encoding to 'iso8859_2'
        elif TransanaGlobal.configData.language == 'easteurope':
            TransanaGlobal.encoding = 'iso8859_2'
        # If we're in Greek, change the encoding to 'iso8859_7'
        elif TransanaGlobal.configData.language == 'el':
            TransanaGlobal.encoding = 'iso8859_7'
        # If we're in Japanese, change the encoding to cp932
        elif TransanaGlobal.configData.language == 'ja':
            TransanaGlobal.encoding = 'cp932'
        # If we're in Korean, change the encoding to cp949
        elif TransanaGlobal.configData.language == 'ko':
            TransanaGlobal.encoding = 'cp949'
        # Otherwise, fall back to Latin-1
        else:
            TransanaGlobal.encoding = 'latin1'
        # If a new database login fails three times, we need to close the program.
        # Initialize a counter to track that.
        logonCount = 1
        # Flag if Logon succeeds
        loggedOn = False
        # Keep trying for three tries or until successful
        while (logonCount <= 3) and (not loggedOn):
            # Increment logon counter
            logonCount += 1
            # Call up the Username and Password Dialog to get new connection information
            if DBInterface.establish_db_exists():
                # Now update the Data Window
                self.DataWindow.DBTab.tree.refresh_tree()
                # Indicate successful logon
                loggedOn = True
            # If logon fails, inform user and offer to try again twice.
            elif logonCount <= 3:
                # Create a Dialog Box
                dlg = Dialogs.QuestionDialog(self.MenuWindow, _('Transana was unable to connect to the database.\nWould you like to try again?'),
                                         _('Transana Database Connection'))
                # If the user does not want to try again, set the counter to 4, which will cause the program to exit
                if dlg.LocalShowModal() == wx.ID_NO:
                    logonCount = 4
                # Clean up the Dialog Box
                dlg.Destroy()
            # If we're in multi-user and we successfully logged in ...
            if not TransanaConstants.singleUserVersion and loggedOn:
                # ... start the Connection Timer.  This attempts to prevent the "Connection to Database Lost" error by
                # running a very small query every 10 minutes.  See Transana.py.
                TransanaGlobal.connectionTimer.Start(600000)
        # If the Database Connection fails ...
        if not loggedOn:
            # ... Close Transana
            self.MenuWindow.OnFileExit(None)

    def ShowDataTab(self, tabValue):
        """ Changes the visible tab in the notebook in the Data Window """
        if self.MenuWindow.menuBar.optionsmenu.IsChecked(MenuSetup.MENU_OPTIONS_PRESENT_ALL):
            # Display the Keywords Tab
            self.DataWindow.nb.SetSelection(tabValue)

    def InsertTimecodeIntoTranscript(self):
        """ Insert a Timecode into the Transcript(s) """
        # For each Transcript window ...
        for trWin in self.TranscriptWindow:
            # ... if the transcript is in Edit mode ...
            if not trWin.dlg.editor.get_read_only():
                # ... get the transcript's selection ...
                selection = trWin.dlg.editor.GetSelection()
                # ... and only if it's a position, not a selection ...
                if selection[0] == selection[1]:
                    # ... then insert the time code.
                    trWin.InsertTimeCode()

    def InsertSelectionTimecodesIntoTranscript(self, startPos, endPos):
        """ Insert a timed pause into the Transcript """
        self.TranscriptWindow[self.activeTranscript].InsertSelectionTimeCode(startPos, endPos)

    def SetTranscriptEditOptions(self, enable):
        """ Change the Transcript's Edit Mode """
        self.MenuWindow.SetTranscriptEditOptions(enable)

    def TranscriptUndo(self, event):
        """ Send an Undo command to the Transcript """
        self.TranscriptWindow[self.activeTranscript].TranscriptUndo(event)

    def TranscriptCut(self):
        """ Send a Cut command to the Transcript """
        self.TranscriptWindow[self.activeTranscript].TranscriptCut()

    def TranscriptCopy(self):
        """ Send a Copy command to the Transcript """
        self.TranscriptWindow[self.activeTranscript].TranscriptCopy()

    def TranscriptPaste(self):
        """ Send a Paste command to the Transcript """
        self.TranscriptWindow[self.activeTranscript].TranscriptPaste()

    def TranscriptCallFontDialog(self):
        """ Tell the TranscriptWindow to open the Font Dialog """
        self.TranscriptWindow[self.activeTranscript].CallFontDialog()

    def Help(self, helpContext):
        """ Handles all calls to the Help System """
        # Getting this to work both from within Python and in the stand-alone executable
        # has been a little tricky.  To get it working right, we need the path to the
        # Transana executables, where Help.exe resides, and the file name, which tells us
        # if we're in Python or not.
        (path, fn) = os.path.split(sys.argv[0])
        
        # If the path is not blank, add the path seperator to the end if needed
        if (path != '') and (path[-1] != os.sep):
            path = path + os.sep

        programName = os.path.join(path, 'Help.py')

        if "__WXMAC__" in wx.PlatformInfo:
            # NOTE:  If we just call Help.Help(), you can't actually do the Tutorial because
            # the Help program's menus override Transana's, and there's no way to get them back.
            # instead of the old call:
            
            # Help.Help(helpContext)
            
            # NOTE:  I've tried a bunch of different things on the Mac without success.  It seems that
            #        the Mac doesn't allow command line parameters, and I have not been able to find
            #        a reasonable method for passing the information to the Help application to tell it
            #        what page to load.  What works is to save the string to the hard drive and 
            #        have the Help file read it that way.  If the user leave Help open, it won't get
            #        updated on subsequent calls, but for now that's okay by me.
            
            helpfile = open(os.getenv("HOME") + '/TransanaHelpContext.txt', 'w')
            pickle.dump(helpContext, helpfile)
            helpfile.flush()
            helpfile.close()

            # On OS X 10.4, when Transana is packed with py2app, the Help call stopped working.
            # It seems we have to remove certain environment variables to get it to work properly!
            # Let's investigate environment variables here!
            envirVars = os.environ
            if 'PYTHONHOME' in envirVars.keys():
                del(os.environ['PYTHONHOME'])
            if 'PYTHONPATH' in envirVars.keys():
                del(os.environ['PYTHONPATH'])
            if 'PYTHONEXECUTABLE' in envirVars.keys():
                del(os.environ['PYTHONEXECUTABLE'])

            os.system('open -a TransanaHelp.app')

        else:
            # NOTE:  If we just call Help.Help(), you can't actually do the Tutorial because 
            # modal dialogs prevent you from focussing back on the Help Window to scroll or
            # advance the Tutorial!  Instead of the old call:
        
            # Help.Help(helpContext)

            # we'll use Python's os.spawn() to create a seperate process for the Help system
            # to run in.  That way, we can go back and forth between Transana and Help as
            # independent programs.
        
            # Make the Help call differently from Python and the stand-alone executable.
            if fn.lower() == 'transana.py':
                # for within Python, we call python, then the Help code and the context
                os.spawnv(os.P_NOWAIT, 'python.bat', [programName, helpContext])
            else:
                # The Standalone requires a "dummy" parameter here (Help), as sys.argv differs between the two versions.
                os.spawnv(os.P_NOWAIT, path + 'Help', ['Help', helpContext])


    # Private Methods
        
    def LoadVideo(self, Filename, mediaStart, mediaLength):
        """ This method handles loading a video in the video window and loading the
            corresponding Visualization in the Visualization window. """
        # Assume this will succeed
        success = True
        # Check for the existence of the Media File
        if not os.path.exists(Filename):
            # We need a different message for single-user and multi-user Transana if the video file cannot be found.
            if TransanaConstants.singleUserVersion:
                # If it does not exist, display an error message Dialog
                prompt = _('Media File "%s" cannot be found.\nPlease locate this media file and press the "Update Database" button.\nThen reload the Transcript or Clip that failed.')
                if 'unicode' in wx.PlatformInfo:
                    # Encode with UTF-8 rather than TransanaGlobal.encoding because this is a prompt, not DB Data.
                    prompt = unicode(prompt, 'utf8')
            else:
                # If it does not exist, display an error message Dialog
                prompt = _('Media File "%s" cannot be found.\nPlease make sure your video root directory is set correctly, and that the video file exists in the correct location.\nThen reload the Transcript or Clip that failed.')
                if 'unicode' in wx.PlatformInfo:
                    # Encode with UTF-8 rather than TransanaGlobal.encoding because this is a prompt, not DB Data.
                    prompt = unicode(prompt, 'utf8')
            dlg = Dialogs.ErrorDialog(self.MenuWindow, prompt % Filename)
            dlg.ShowModal()
            dlg.Destroy()
            # Indicate that LoadVideo failed.
            success = False
        else:
            # If the Visualization Window is visible, open the Visualization in the Visualization Window.
            # Loading Visualization first prevents problems with video being locked by Media Player
            # and thus unavailable for wceraudio DLL/Shared Library for audio extraction (in theory).
            self.VisualizationWindow.load_image(Filename, mediaStart, mediaLength)

            # Now that the Visualization is done, load the video in the Video Window
            self.VideoFilename = Filename                # Remember the Video File Name

            # Open the video in the Video Window if the file is found
            self.VideoWindow.open_media_file(Filename)
        # Let the calling routine know if we were successful
        return success

    def ClearVisualizationSelection(self):
        """ Clear the current selection from the Visualization Window """
        self.VisualizationWindow.ClearVisualizationSelection()

    def ChangeVisualization(self):
        """ Triggers a complete refresh of the Visualization Window.  Needed for changing Visualization Style. """
        # Capture the Transcript Window's cursor position
        self.SaveAllTranscriptCursors()
        # Update the Visualization Window
        self.VisualizationWindow.Refresh()
        # Restore the Transcript Window's cursor
        self.RestoreAllTranscriptCursors()

    def UpdateKeywordVisualization(self):
        """ If the Keyword Visualization is displayed, update it based on something that could change the keywords
            in the display area. """
        self.VisualizationWindow.UpdateKeywordVisualization()

    def Play(self, setback=False):
        """ This method starts video playback from the current video position. """
        # If we do not already have a cursor position saved, save it
        if self.TranscriptWindow[self.activeTranscript].dlg.editor.cursorPosition == 0:
            self.TranscriptWindow[self.activeTranscript].dlg.editor.SaveCursor()
        # If Setback is requested (Transcription Ctrl-S)
        if setback:
            # Get the current Video position
            videoPos = self.VideoWindow.GetCurrentVideoPosition()
            if type(self.currentObj).__name__ == 'Episode':
                videoStart = 0
            elif type(self.currentObj).__name__ == 'Clip':
                videoStart = self.currentObj.clip_start
            else:
                # Get the current Video marker
                videoStart = self.VideoWindow.GetVideoStartPoint()
            # Assertation: videoPos >= videoStart
            # Find the configured Setback Size (convert to milliseconds)
            setbackSize = TransanaGlobal.configData.transcriptionSetback * 1000
            # If you are further into the video than the Seback Size ...
            if videoPos - videoStart > setbackSize:
                # ... jump back in the video by the setback size
                self.VideoWindow.SetCurrentVideoPosition(videoPos - setbackSize)
            # If the setback would take you to before the beginning of video marker ...
            else:
                # ... jump to the beginning of the video marker
                self.VideoWindow.SetCurrentVideoPosition(videoStart)

        # We need to explicitly set the Clip Endpoint, if it's not known.
        # If nothing is loaded, currentObj will be None.  Check to avoid an error.
        if (self.VideoEndPoint == -1) and (self.currentObj != None):
            if type(self.currentObj).__name__ == 'Episode':
                videoEnd = self.currentObj.tape_length
            elif type(self.currentObj).__name__ == 'Clip':
                videoEnd = self.currentObj.clip_stop
            self.SetVideoEndPoint(videoEnd)
        # Play the Video
        self.VideoWindow.Play()

    def Stop(self):
        """ This method stops video playback.  Stop causes the video to be repositioned at the VideoStartPoint. """
        self.VideoWindow.Stop()
        self.RestoreAllTranscriptCursors()

    def Pause(self):
        """ This method pauses video playback.  Pause does not alter the video position, so play will continue from where pause was called. """
        self.VideoWindow.Pause()

    def PlayPause(self, setback=False):
        """ If the video is playing, this pauses it.  If the video is paused, this will make it play. """
        if self.VideoWindow.IsPlaying():
            self.Pause()
        elif self.VideoWindow.IsPaused() or self.VideoWindow.IsStopped():
            self.Play(setback)
        else: # If not playing, paused or stopped, then video not loaded yet
            pass

    def PlayStop(self, setback=False):
        """ If the video is playing, this pauses it.  If the video is paused, this will make it play. """
        if self.VideoWindow.IsPlaying():
            self.Stop()
        elif self.VideoWindow.IsPaused() or self.VideoWindow.IsStopped():
            self.Play(setback)
        else: # If not playing, paused or stopped, then video not loaded yet
            pass

    def IsPlaying(self):
        """ Indicates whether the video is playing or not. """
        return self.VideoWindow.IsPlaying()

    def IsPaused(self):
        """ Indicates whether the video is paused or not. """
        return self.VideoWindow.IsPaused()

    def IsLoading(self):
        """ Indicates whether the video is loading into the Player or not. """
        return self.VideoWindow.IsLoading()

    def GetVideoStartPoint(self):
        """ Return the current Video Starting Point """
        return self.VideoStartPoint
    
    def SetVideoStartPoint(self, TimeCode):
        """ Set the Starting Point for video segment definition.  0 is the start of the video.  TimeCode is the nunber of milliseconds from the beginning. """
        # If we are passed a negative time code ...
        if TimeCode < 0:
            # ... set the time code to 0, the start of the video
            TimeCode = 0
        self.VideoWindow.SetVideoStartPoint(TimeCode)
        self.VideoStartPoint = TimeCode

    def GetVideoEndPoint(self):
        """ Return the current Video Ending Point """
        if self.VideoEndPoint > 0:
            return self.VideoEndPoint
        else:
            return self.VideoWindow.GetMediaLength()

    def SetVideoEndPoint(self, TimeCode):
        """ Set the Stopping Point for video segment definition.  0 is the end of the video.  TimeCode is the nunber of milliseconds from the beginning. """
        self.VideoWindow.SetVideoEndPoint(TimeCode)
        self.VideoEndPoint = TimeCode

    def GetVideoSelection(self):
        """ Return the current video starting and ending points """
        return (self.VideoStartPoint, self.VideoEndPoint)

    def SetVideoSelection(self, StartTimeCode, EndTimeCode):
        """ Set the Starting and Stopping Points for video segment definition.  TimeCodes are in milliseconds from the beginning. """
        # For each Transcript Window ...
        for trWin in self.TranscriptWindow:
            # ... if the Window is Read Only (not in Edit mode) ...
            if trWin.dlg.editor.get_read_only():
                # Sometime the cursor is positioned at the end of the selection rather than the beginning, which can cause
                # problems with the highlight.  Let's fix that if needed.
                if trWin.dlg.editor.GetCurrentPos() != trWin.dlg.editor.GetSelection()[0]:
                    (start, end) = trWin.dlg.editor.GetSelection()
                    trWin.dlg.editor.SetCurrentPos(start)
                    trWin.dlg.editor.SetAnchor(end)
                    
                # If Word Tracking is ON ...
                if TransanaGlobal.configData.wordTracking:
                    # ... highlight the full text of the video selection
                    trWin.dlg.editor.scroll_to_time(StartTimeCode)

                    if EndTimeCode > 0:
                        trWin.dlg.editor.select_find(str(EndTimeCode))
            # Save the cursor position.  Otherwise, the previous incorrect value gets restored later.
            trWin.dlg.editor.SaveCursor()
                
        if EndTimeCode <= 0:
            if type(self.currentObj).__name__ == 'Episode':
                EndTimeCode = self.VideoWindow.GetMediaLength()
            elif type(self.currentObj).__name__ == 'Clip':
                EndTimeCode = self.currentObj.clip_stop
            
        self.SetVideoStartPoint(StartTimeCode)
        self.SetVideoEndPoint(EndTimeCode)
        # The SelectedEpisodeClips window was not updating on the Mac.  Therefore, this was added,
        # even if it might be redundant on Windows.
        if (not self.IsPlaying()) or (self.TranscriptWindow[self.activeTranscript].UpdatePosition(StartTimeCode)):
            if self.DataWindow.SelectedEpisodeClipsTab != None:
                self.DataWindow.SelectedEpisodeClipsTab.Refresh(StartTimeCode)
        # Update the Selection Text in the current Transcript Window.  But it needs just a tick before the cursor position is set correctly.
        wx.CallLater(50, self.UpdateSelectionTextLater, self.activeTranscript)
        
        
    def UpdatePlayState(self, playState):
        """ When the Video Player's Play State Changes, we may need to adjust the Screen Layout
            depending on the Presentation Mode settings. """
        
        # If the video is STOPPED, return all windows to normal Transana layout
        if (playState == TransanaConstants.MEDIA_PLAYSTATE_STOP) and (self.PlayAllClipsWindow == None):
            # When Play is intiated (below), the positions of windows gets saved if they are altered by Presentation Mode.
            # If this has happened, we need to put the screen back to how it was before when Play is stopped.
            if len(self.WindowPositions) != 0:
                # Reset the AutoArrange (which was temporarily disabled for Presentation Mode) variable based on the Menu Setting
                TransanaGlobal.configData.autoArrange = self.MenuWindow.menuBar.optionsmenu.IsChecked(MenuSetup.MENU_OPTIONS_AUTOARRANGE)
                # Reposition the Video Window to its original Position (self.WindowsPositions[2])
                self.VideoWindow.SetDims(self.WindowPositions[2][0], self.WindowPositions[2][1], self.WindowPositions[2][2], self.WindowPositions[2][3])
                # Unpack the Transcript Window Positions
                for winNum in range(len(self.WindowPositions[3])):
                    # Reposition each Transcript Window to its original Position (self.WindowsPositions[3])
                    self.TranscriptWindow[winNum].SetDims(self.WindowPositions[3][winNum][0], self.WindowPositions[3][winNum][1], self.WindowPositions[3][winNum][2], self.WindowPositions[3][winNum][3])
                # Show the Menu Bar
                self.MenuWindow.Show(True)
                # Show the Visualization Window
                self.VisualizationWindow.Show(True)
                # Show all Transcript Windows
                for trWindow in self.TranscriptWindow:
                    trWindow.Show(True)
                # Show the Data Window
                self.DataWindow.Show(True)
                # Clear the saved Window Positions, so that if they are moved, the new settings will be saved when the time comes
                self.WindowPositions = []
            # Reset the Transcript Cursors
            self.RestoreAllTranscriptCursors()
                
        # If the video is PLAYED, adjust windows to the desired screen layout,
        # as indicated by the Presentation Mode selection
        elif playState == TransanaConstants.MEDIA_PLAYSTATE_PLAY:
            # If we are starting up from the Video Window, save the Transcript Cursor.
            # Detecting that the Video Window has focus is hard, as there are different video window implementations on
            # different platforms.  Therefore, let's see if it's NOT the Transcript or the Waveform, which are easier to
            # detect.
            if (type(self.MenuWindow.FindFocus()) != type(self.TranscriptWindow[self.activeTranscript].dlg.editor)) and \
               ((self.MenuWindow.FindFocus()) != (self.VisualizationWindow.waveform)):
                self.TranscriptWindow[self.activeTranscript].dlg.editor.SaveCursor()
            # See if Presentation Mode is NOT set to "All Windows" and do all changes common to the other Presentation Modes
            if self.MenuWindow.menuBar.optionsmenu.IsChecked(MenuSetup.MENU_OPTIONS_PRESENT_ALL) == False:
                # See if we have already noted the Window Positions.
                if len(self.WindowPositions) == 0:
                    # If not...
                    # Temporarily disable AutoArrange, as it interferes with Presentation Mode
                    TransanaGlobal.configData.autoArrange = False
                    # Get the Window Positions for all Transcript windows
                    transcriptWindowPositions = []
                    for trWin in self.TranscriptWindow:
                        transcriptWindowPositions.append(trWin.GetDimensions())
                    # Save the Window Positions prior to Presentation Mode rearrangement
                    self.WindowPositions = [self.MenuWindow.GetRect(),
                                            self.VisualizationWindow.GetDimensions(),
                                            self.VideoWindow.GetDimensions(),
                                            transcriptWindowPositions,
                                            self.DataWindow.GetDimensions()]
                # Hide the Menu Window
                self.MenuWindow.Show(False)
                # Hide the Visualization Window
                self.VisualizationWindow.Show(False)
                # Hide the Data Window
                self.DataWindow.Show(False)
                # Determine the size of the screen
                (left, top, width, height) = wx.ClientDisplayRect()

                # See if Presentation Mode is set to "Video Only"
                if self.MenuWindow.menuBar.optionsmenu.IsChecked(MenuSetup.MENU_OPTIONS_PRESENT_VIDEO):
                    # Hide the Transcript Windows
                    for trWindow in self.TranscriptWindow:
                        trWindow.Show(False)
                    # Set the Video Window to take up almost the whole Client Display area
                    self.VideoWindow.SetDims(left + 2, top + 2, width - 4, height - 4)
                    # If there is a PlayAllClipsWindow, reset it's size and layout
                    if self.PlayAllClipsWindow != None:
                        # Set the Window Position in the PlayAllClips Dialog
                        self.PlayAllClipsWindow.xPos = left + 2
                        self.PlayAllClipsWindow.yPos = height - 58
                        # We need a bit more adjustment on the Mac
                        if 'wxMac' in wx.PlatformInfo:
                            self.PlayAllClipsWindow.yPos += 24
                        self.PlayAllClipsWindow.SetRect(wx.Rect(self.PlayAllClipsWindow.xPos, self.PlayAllClipsWindow.yPos, width - 4, 56))
                        # Make the PlayAllClipsWindow the focus
                        self.PlayAllClipsWindow.SetFocus()

                # See if Presentation Mode is set to "Video and Transcript"
                if self.MenuWindow.menuBar.optionsmenu.IsChecked(MenuSetup.MENU_OPTIONS_PRESENT_TRANS):
                    # We need to make a slight adjustment for the Mac for the menu height
                    if 'wxMac' in wx.PlatformInfo:
                        height += TransanaGlobal.menuHeight
                    # Set the Video Window to take up the top 70% of the Client Display Area
                    self.VideoWindow.SetDims(left + 2, top + 2, width - 4, int(0.7 * height) - 3)
                    # Set the Transcript Window to take up the bottom 30% of the Client Display Area
                    self.TranscriptWindow[0].SetDims(left + 2, int(0.7 * height) + 1, width - 4, int(0.3 * height) - 4)
                    # Hide the other Transcript Windows
                    for trWindow in self.TranscriptWindow[1:]:
                        trWindow.Show(False)
                    # If there is a PlayAllClipsWindow, reset it's size and layout
                    if self.PlayAllClipsWindow != None:
                        # Set the Window Position in the PlayAllClips Dialog
                        self.PlayAllClipsWindow.xPos = left + 2
                        self.PlayAllClipsWindow.yPos = int(0.7 * height) - 58
                        self.PlayAllClipsWindow.SetRect(wx.Rect(self.PlayAllClipsWindow.xPos, self.PlayAllClipsWindow.yPos, width - 4, 56))
                        # Make the PlayAllClipsWindow the focus
                        self.PlayAllClipsWindow.SetFocus()
        

    def GetDatabaseDims(self):
        """ Return the dimensions of the Database control. Note that this only returns the Database Tree Tab location.  """
        # Determine the Screen Position of the top left corner of the Tree Control
        (treeLeft, treeTop) = self.DataWindow.DBTab.tree.ClientToScreenXY(1, 1)
        # Determine the width and height of the tree control
        (width, height) = self.DataWindow.DBTab.tree.GetSizeTuple()
        # Return the Database Tree Tab position and size information
        return (treeLeft, treeTop, width, height)

    def GetTranscriptDims(self):
        """ Return the dimensions of the transcript control.  Note that this only includes the transcript itself
        and not the whole Transcript window (including toolbars, etc). """
        return self.TranscriptWindow[self.activeTranscript].GetTranscriptDims()

    def GetCurrentTranscriptObject(self):
        """ Returns a Transcript Object for the Transcript currently loaded in the Transcript Editor """
        return self.TranscriptWindow[self.activeTranscript].GetCurrentTranscriptObject()

    def GetTranscriptSelectionInfo(self):
        """ Returns information about the current selection in the transcript editor """
        # We need to know the time codes that bound the current selection
        (startTime, endTime) = self.TranscriptWindow[self.activeTranscript].dlg.editor.get_selected_time_range()
        # we need to know the text of the current selection
        # If it's blank, we need to send a blank rather than RTF for nothing
        (startPos, endPos) = self.TranscriptWindow[self.activeTranscript].dlg.editor.GetSelection()
        # If there's no current selection ...
        if startPos == endPos:
            # ... get the text between the nearest time codes.
            (st, end, text) = self.TranscriptWindow[self.activeTranscript].dlg.editor.GetTextBetweenTimeCodes(startTime, endTime)
        else:
            text = self.TranscriptWindow[self.activeTranscript].dlg.editor.GetRTFBuffer(select_only=1)
        # We also need to know the number of the original Transcript Record
        if self.TranscriptWindow[self.activeTranscript].dlg.editor.TranscriptObj.clip_num == 0:
            # If we have an Episode Transcript, we need the Transcript Number
            originalTranscriptNum = self.TranscriptWindow[self.activeTranscript].dlg.editor.TranscriptObj.number
        else:
            # If we have a Clip Transcript, we need the original Transcript Number, not the Clip Transcript Number.
            # We can get that from the ControlObject's "currentObj", which in this case will be the Clip!
            originalTranscriptNum = self.currentObj.transcript_num
        return (originalTranscriptNum, startTime, endTime, text)

    def GetMultipleTranscriptSelectionInfo(self):
        """ Returns information about the current selection(s) in the transcript editor(s) """
        # Initialize a list for the function results
        results = []
        # Iterate through the transcript windows
        for trWindow in self.TranscriptWindow:
            # We need to know the time codes that bound the current selection in the current transcript window
            (startTime, endTime) = trWindow.dlg.editor.get_selected_time_range()
            # If start is 0 ...
            if startTime == 0:
                # ... and we're in a Clip ...
                if isinstance(self.currentObj, Clip.Clip):
                    # ... then the start should be the Clip Start
                    startTime = self.currentObj.clip_start
            # If there is not following time code ...
            if endTime <= 0:
                # ... and we're in a Clip ...
                if isinstance(self.currentObj, Clip.Clip):
                    # ... use the Clip Stop value ...
                    endTime = self.currentObj.clip_stop
                # ... otherwise ...
                else:
                    # ... use the length of the media file
                    endTime = self.GetMediaLength(entire = True)
            # we need to know the text of the current selection in the current transcript window
            # If it's blank, we need to send a blank rather than RTF for nothing
            (startPos, endPos) = trWindow.dlg.editor.GetSelection()
            if startPos == endPos:
                text = ''
            else:
                text = trWindow.dlg.editor.GetRTFBuffer(select_only=1)
            # We also need to know the number of the original Transcript Record.  If we have an Episode ....
            if trWindow.dlg.editor.TranscriptObj.clip_num == 0:
                # ... we need the Transcript Number, which we can get from the Transcript Window's editor's Transcript Object
                originalTranscriptNum = trWindow.dlg.editor.TranscriptObj.number
            # If we have a Clip ...
            else:
                # ... we need the original Transcript Number, not the Clip Transcript Number.
                # We can get that from the ControlObject's "currentObj", which in this case will be the Clip!
                # We have to pull the source_transcript value from the correct transcript number!
                originalTranscriptNum = self.currentObj.transcripts[self.TranscriptWindow.index(trWindow)].source_transcript
            # Now we can place this transcript's results into the Results list
            results.append((originalTranscriptNum, startTime, endTime, text))
        return results

    def GetDatabaseTreeTabObjectNodeType(self):
        """ Get the Node Type of the currently selected object in the Database Tree in the Data Window """
        return self.DataWindow.DBTab.tree.GetObjectNodeType()

    def SetDatabaseTreeTabCursor(self, cursor):
        """ Change the shape of the cursor for the database tree in the data window """
        self.DataWindow.DBTab.tree.SetCursor(wx.StockCursor(cursor))

    def GetVideoPosition(self):
        """ Returns the current Time Code from the Video Window """
        return self.VideoWindow.GetCurrentVideoPosition()
        
    def UpdateVideoPosition(self, currentPosition):
        """ This method accepts the currentPosition from the video window and propagates that position to other objects """
        # There's a weird glitch with Play All Clips when switching from one multi-transcript clip to the next.
        # Somehow, activeTranscript is getting set to a TranscriptWindow that hasn't yet been created, and that's
        # causing a problem HERE.  The following lines of code fix it.  I haven't been able to track down the cause.
        if self.activeTranscript >= len(self.TranscriptWindow):
            # We need to reset the activeTranscript to 0.  It gets reset later when this line is triggered.
            self.activeTranscript = 0

        # If we do not already have a cursor position saved, and there is a defined cursor position, save it
        if (self.TranscriptWindow[self.activeTranscript].dlg.editor.cursorPosition == 0) and \
           (self.TranscriptWindow[self.activeTranscript].dlg.editor.GetCurrentPos() != 0) and \
           (self.TranscriptWindow[self.activeTranscript].dlg.editor.GetSelection() != (0, 0)):
            self.TranscriptWindow[self.activeTranscript].dlg.editor.SaveCursor()
            
        if self.VideoEndPoint > 0:
            mediaLength = self.VideoEndPoint - self.VideoStartPoint
        else:
            mediaLength = self.VideoWindow.GetMediaLength()
        self.VisualizationWindow.UpdatePosition(currentPosition)

        # Update Transcript position.  If Transcript position changes,
        # then also update the selected Clips tab in the Data window.
        # NOTE:  self.IsPlaying() check added because the SelectedEpisodeClips Tab wasn't updating properly
        if (not self.IsPlaying()) or (self.TranscriptWindow[self.activeTranscript].UpdatePosition(currentPosition)):
            if self.DataWindow.SelectedEpisodeClipsTab != None:
                self.DataWindow.SelectedEpisodeClipsTab.Refresh(currentPosition)

        # Update all Transcript Windows
        for winNum in range(len(self.TranscriptWindow)):
            self.TranscriptWindow[winNum].UpdatePosition(currentPosition)
            self.UpdateSelectionTextLater(winNum)

    def UpdateSelectionTextLater(self, winNum):
        """ Update the Selection Text after the application has had a chance to update the Selection information """
        # When closing windows, we run into trouble.  Check to be sure the window exists to start!
        if winNum in range(len(self.TranscriptWindow)):
            # Get the current selection
            selection = self.TranscriptWindow[winNum].dlg.editor.GetSelection()
            # If we have a point rather than a selection ...
            if selection[0] == selection[1]:
                # We don't need a label
                lbl = ""
            # If we have a selection rather than a point ...
            else:
                # ... we first need to get the time range of the current selection.
                (start, end) = self.TranscriptWindow[winNum].dlg.editor.get_selected_time_range()
                # If start is 0 ...
                if start == 0:
                    # ... and we're in a Clip ...
                    if isinstance(self.currentObj, Clip.Clip):
                        # ... then the start should be the Clip Start
                        start = self.currentObj.clip_start
                # If there is not following time code ...
                if end <= 0:
                    # ... and we're in a Clip ...
                    if isinstance(self.currentObj, Clip.Clip):
                        # ... use the Clip Stop value ...
                        end = self.currentObj.clip_stop
                    # ... otherwise ...
                    else:
                        # ... use the length of the media file
                        end = self.GetMediaLength(entire = True)
                # Then we build the label.
                lbl = _("Selection:  %s - %s")
                if 'unicode' in wx.PlatformInfo:
                    lbl = unicode(lbl, 'utf8')
                lbl = lbl % (Misc.time_in_ms_to_str(start), Misc.time_in_ms_to_str(end))
            # Now display the label on the Transcript Window.
            self.TranscriptWindow[winNum].UpdateSelectionText(lbl)

    def GetMediaLength(self, entire = False):
        """ This method returns the length of the entire video/media segment """
        try:
            if not(entire): # Return segment length
                if self.VideoEndPoint <= 0:
                    videoLength = self.VideoWindow.GetMediaLength()
                    mediaLength = videoLength - self.VideoStartPoint

                    # Sometimes video files don't know their own length because it hasn't been available before.
                    # This may be a good place to detect and correct that problem before it starts to cause problems,
                    # such as in the Keyword Map.

                    # First, let's see if we have a chance to detect and correct the problem by seeing if an episode is
                    # currently loaded that doesn't have a proper length.
                    if (type(self.currentObj).__name__ == 'Episode') and \
                       (self.currentObj.media_filename == self.VideoFilename) and \
                       (self.currentObj.tape_length <= 0) and \
                       (videoLength > 0):
                            try:
                                self.currentObj.lock_record()
                                self.currentObj.tape_length = videoLength
                                self.currentObj.db_save()
                                self.currentObj.unlock_record()
                            except:
                                pass

                else:
                    if self.VideoEndPoint - self.VideoStartPoint > 0:
                        mediaLength = self.VideoEndPoint - self.VideoStartPoint
                    else:
                        mediaLength = self.VideoWindow.GetMediaLength() - self.VideoStartPoint
                return mediaLength
            else: # Return length of entire video 
                return self.VideoWindow.GetMediaLength()
        except:
            # If an exception is raised, most likely we're shutting down and have lost the VideoWindow.  Just return 0.
            return 0
        
    def UpdateVideoWindowPosition(self, left, top, width, height):
        """ This method receives screen position and size information from the Video Window and adjusts all other windows accordingly """
        if TransanaGlobal.configData.autoArrange:
            # Visualization Window adjusts WIDTH only to match shift in video window
            (wleft, wtop, wwidth, wheight) = self.VisualizationWindow.GetDimensions()
            self.VisualizationWindow.SetDims(wleft, wtop, left - wleft - 4, wheight)

            # NOTE:  We only need to trigger Visualization and Data windows' SetDims method to resize everything!

            # Data Window matches Video Window's width and shifts top and height to accommodate shift in video window
            (wleft, wtop, wwidth, wheight) = self.DataWindow.GetDimensions()
            self.DataWindow.SetDims(left, top + height + 4, width, wheight - (top + height + 4 - wtop))

            # Play All Clips Window matches the Data Window's WIDTH
            if self.PlayAllClipsWindow != None:
                (parentLeft, parentTop, parentWidth, parentHeight) = self.DataWindow.GetRect()
                (left, top, width, height) = self.PlayAllClipsWindow.GetRect()
                if (parentWidth != width):
                    self.PlayAllClipsWindow.SetDimensions(parentLeft, top, parentWidth, height)

    def UpdateWindowPositions(self, sender, X, YUpper=-1, YLower=-1):
        """ This method updates all window sizes/positions based on the intersection point passed in.
            X is the horizontal point at which the visualization and transcript windows end and the
            video and data windows begin.
            YUpper is the vertical point where the visualization window ends and the transcript window begins.
            YLower is the vertical point where the video window ends and the data window begins. """
        # We need to adjust the Window Positions to accomodate multiple transcripts!
        # Basically, if we are not in the "first" transcript, we need to substitute the first transcript's
        # "Top position" value for the one sent by the active window.
        if (sender == 'Transcript'):
            YUpper = self.TranscriptWindow[0].dlg.GetPositionTuple()[1] - 4
        # If Auto-Arrange is enabled, resizing one window may alter the positioning of others.
        if TransanaGlobal.configData.autoArrange:

            if YUpper == -1:
                (wleft, wtop, wwidth, wheight) = self.VisualizationWindow.GetDimensions()
                YUpper = wheight + wtop      
            if YLower == -1:
                (wleft, wtop, wwidth, wheight) = self.VideoWindow.GetDimensions()
                YLower = wheight + wtop
                
            if sender != 'Visualization':
                # Adjust Visualization Window
                (wleft, wtop, wwidth, wheight) = self.VisualizationWindow.GetDimensions()
                self.VisualizationWindow.SetDims(wleft, wtop, X - wleft, YUpper - wtop)

            if sender != 'Transcript':
                # Adjust Transcript Window
                (wleft, wtop, wwidth, wheight) = self.TranscriptWindow[0].GetDimensions()
                self.TranscriptWindow[0].SetDims(wleft, YUpper + 4, X - wleft, wheight + (wtop - YUpper - 4))

            if len(self.TranscriptWindow) > 1:
                self.AutoArrangeTranscriptWindows()

            if sender != 'Video':
                # Adjust Video Window
                (wleft, wtop, wwidth, wheight) = self.VideoWindow.GetDimensions()
                self.VideoWindow.SetDims(X + 4, wtop, wwidth + (wleft - X - 4), YLower - wtop)

            if sender != 'Data':
                # Adjust Data Window
                (wleft, wtop, wwidth, wheight) = self.DataWindow.GetDimensions()
                self.DataWindow.SetDims(X + 4, YLower + 4, wwidth + (wleft - X - 4), wheight + (wtop - YLower - 4))

    def VideoSizeChange(self):
        """ Signal that the Video Size has been changed via the Options > Video menu """
        # Resize the video window.  This will trigger changes in all the other windows as appropriate.
        self.VideoWindow.frame.OnSizeChange()

    def SaveTranscript(self, prompt=0, cleardoc=0, transcriptToSave=-1):
        """Save the Transcript to the database if modified.  If prompt=1,
        prompt the user to confirm the save.  Return 1 if Transcript was
        saved or unchanged, and 0 if user chose to discard changes.  If
        cleardoc=1, then the transcript will be cleared if the user chooses
        to not save."""
        # NOTE:  When the user presses their response to dlg below, it can shift the focus if there are multiple
        #        transcript windows open!  Therefore, remember which transcript we're working on now.
        if transcriptToSave == -1:
            transcriptToSave = self.activeTranscript
        # Was the document modified?
        if self.TranscriptWindow[transcriptToSave].TranscriptModified():
            result = wx.ID_YES
           
            if prompt:
                if self.TranscriptWindow[transcriptToSave].dlg.editor.TranscriptObj.clip_num > 0:
                    pmpt = _("The Clip Transcript has changed.\nDo you want to save it before continuing?")
                else:
                    pmpt = _('Transcript "%s" has changed.\nDo you want to save it before continuing?')
                    if 'unicode' in wx.PlatformInfo:
                        pmpt = unicode(pmpt, 'utf8')
                    pmpt = pmpt % self.TranscriptWindow[transcriptToSave].dlg.editor.TranscriptObj.id
                dlg = Dialogs.QuestionDialog(None, pmpt, _("Question"))
                result = dlg.LocalShowModal()
                dlg.Destroy()
                self.activeTranscript = transcriptToSave
            
            if result == wx.ID_YES:
                try:
                    self.TranscriptWindow[transcriptToSave].SaveTranscript()
                    return 1
                except TransanaExceptions.SaveError, e:
                    dlg = Dialogs.ErrorDialog(None, e.reason)
                    dlg.ShowModal()
                    dlg.Destroy()
                    return 1
            else:
                if cleardoc:
                    self.TranscriptWindow[transcriptToSave].ClearDoc()
                return 0
        return 1

    def SaveTranscriptAs(self):
        """Export the Transcript to an RTF file."""
        dlg = wx.FileDialog(None, wildcard="*.rtf", style=wx.SAVE)
        if dlg.ShowModal() == wx.ID_OK:
            fname = dlg.GetPath()
            # Mac doesn't automatically append the file extension.  Do it if necessary.
            if not fname.upper().endswith(".RTF"):
                fname += '.rtf'
            if os.path.exists(fname):
                if 'unicode' in wx.PlatformInfo:
                    # Encode with UTF-8 rather than TransanaGlobal.encoding because this is a prompt, not DB Data.
                    prompt = unicode(_('A file named "%s" already exists.  Do you want to replace it?'), 'utf8')
                else:
                    prompt = _('A file named "%s" already exists.  Do you want to replace it?')
                dlg2 = Dialogs.QuestionDialog(None, prompt % fname,
                                        _('Transana Confirmation'))
                dlg2.CentreOnScreen()
                if dlg2.LocalShowModal() == wx.ID_YES:
                    self.TranscriptWindow[self.activeTranscript].SaveTranscriptAs(fname)
                dlg2.Destroy()
            else:
                self.TranscriptWindow[self.activeTranscript].SaveTranscriptAs(fname)
        dlg.Destroy()

    def PropagateChanges(self, transcriptWindowNumber):
        """ Propagate changes in an Episode transcript down to derived clips """
        # First, let's save the changes in the Transcript.  We don't want to propagate changes, then end up
        # not saving them in the source!
        if self.SaveTranscript(prompt=1):
            # If we are working with an Episode Transcript ...
            if type(self.currentObj).__name__ == 'Episode':
                # Start up the Propagate Episode Transcript Changes tool
                propagateDlg = PropagateEpisodeChanges.PropagateEpisodeChanges(self)
            # If we are working with a Clip Transcript ...
            elif type(self.currentObj).__name__ == 'Clip':
                # If the user has updated the clip's Keywords, self.currentObj will NOT reflect this.
                # Therefore, we need to load a new copy of the clip to get the latest keywords for propagation.
                tempClip = Clip.Clip(self.currentObj.number)
                # Start up the Propagate Clip Changes tool
                propagateDlg = PropagateEpisodeChanges.PropagateClipChanges(self.MenuWindow,
                                                                            self.currentObj,
                                                                            transcriptWindowNumber,
                                                                            self.TranscriptWindow[transcriptWindowNumber].dlg.editor.GetRTFBuffer(),
                                                                            newKeywordList=tempClip.keyword_list)

        # If the user chooses NOT to save the Transcript changes ...
        else:
            # ... let them know that nothing was propagated!
            dlg = Dialogs.InfoDialog(None, _("You must save the transcript if you want to propagate the changes."))
            dlg.ShowModal()
            dlg.Destroy()

    def MultiSelect(self, transcriptWindowNumber):
        """ Make selections in all other transcripts to match the selection in the identified transcript """
        # Determine the start and end times of the selection in the identified transcript window
        (start, end) = self.TranscriptWindow[transcriptWindowNumber].dlg.editor.get_selected_time_range()
        # If start is 0 ...
        if start == 0:
            # ... and we're in a Clip ...
            if isinstance(self.currentObj, Clip.Clip):
                # ... then the start should be the Clip Start
                start = self.currentObj.clip_start
        # If there is not following time code ...
        if end <= 0:
            # ... and we're in a Clip ...
            if isinstance(self.currentObj, Clip.Clip):
                # ... use the Clip Stop value ...
                end = self.currentObj.clip_stop
            # ... otherwise ...
            else:
                # ... use the length of the media file
                end = self.GetMediaLength(entire = True)
        # Iterate through all Transcript Windows
        for trWin in self.TranscriptWindow:
            # If we have a transcript window other than the identified one ...
            if trWin.transcriptWindowNumber != transcriptWindowNumber:
                # ... highlight the full text of the video selection
                trWin.dlg.editor.scroll_to_time(start)
                trWin.dlg.editor.select_find(str(end))
            # Once selections are set (later), update the Selection Text
            wx.CallLater(200, self.UpdateSelectionTextLater, trWin.transcriptWindowNumber)
                
    def MultiPlay(self):
        """ Play the current video based on selections in multiple transcripts """
        self.SaveAllTranscriptCursors()
        # Get the Transcript Selection information from all transcript windows.
        transcriptSelectionInfo = self.GetMultipleTranscriptSelectionInfo()
        # Initialize the clip start time to the end of the media file
        earliestStartTime = self.GetMediaLength(True)
        # Initialise the clip end time to the beginning of the media file
        latestEndTime = 0
        # Iterate through the Transcript Selection Info gathered above
        for (transcriptNum, startTime, endTime, text) in transcriptSelectionInfo:
            # If the transcript HAS a selection ...
            if text != "":
                # Check to see if this transcript starts before our current earliest start time, but only if
                # if actually contains text.
                if (startTime < earliestStartTime) and (text != ''):
                    # If so, this is our new earliest start time.
                    earliestStartTime = startTime
                # Check to see if this transcript ends after our current latest end time, but only if
                # if actually contains text.
                if (endTime > latestEndTime) and (text != ''):
                    # If so, this is our new latest end time.
                    latestEndTime = endTime
        # Set the Video Selection to the boundary times
        self.SetVideoSelection(earliestStartTime, latestEndTime)
        # Play the video selection!
        self.Play()

    def UpdateDataWindow(self):
        """ Update the Data Window, as when the "Update Database Window" command is issued """
        # NOTE:  This is called in MU when one user imports a database while another user is connected.
        # Tell the Data Window's Database Tree Tab's Tree to refresh itself
        self.DataWindow.DBTab.tree.refresh_tree()

    def DataWindowHasSearchNodes(self):
        """ Returns the number of Search Nodes in the DataWindow's Database Tree """
        searchNode = self.DataWindow.DBTab.tree.select_Node((_('Search'),), 'SearchRootNode')
        return self.DataWindow.DBTab.tree.ItemHasChildren(searchNode)

    def RemoveDataWindowKeywordExamples(self, keywordGroup, keyword, clipNum):
        """ Remove Keyword Examples from the Data Window """
        # First, remove the Keyword Example from the Database Tree
        # Load the specified Clip record
        tempClip = Clip.Clip(clipNum)
        # Prepare the Node List for removing the Keyword Example Node
        nodeList = (_('Keywords'), keywordGroup, keyword, tempClip.id)
        # Call the DB Tree's delete_Node method.  Include the Clip Record Number so the correct Clip entry will be removed.
        self.DataWindow.DBTab.tree.delete_Node(nodeList, 'KeywordExampleNode', tempClip.number)

    def UpdateDataWindowKeywordsTab(self):
        """ Update the Keywords Tab in the Data Window """
        # If the Keywords Tab is the currently displayed tab ...
        if self.DataWindow.nb.GetPageText(self.DataWindow.nb.GetSelection()) == unicode(_('Keywords'), 'utf8'):
            # ... then refresh the Tab
            self.DataWindow.KeywordsTab.Refresh()

    def CreateQuickClip(self):
        """ Trigger the creation of a Quick Clip from outside of the Database Tree """
        # First, let's see if a Keyword is selected in the Database Tree.  That's required.
        (nodeName, nodeRecNum, nodeParent, nodeType) = self.DataWindow.DBTab.GetSelectedNodeInfo()
        # A Keyword MUST be selected, or we don't know what keyword to base the Quick Clip on
        if nodeType == 'KeywordNode':
            # Get the Transcript Selection information from the ControlObject, since we can't communicate with the
            # TranscriptEditor directly.
            (transcriptNum, startTime, endTime, text) = self.GetTranscriptSelectionInfo()
            # Initialize the Episode Number to 0
            episodeNum = 0
            # If our source is an Episode ...
            if isinstance(self.currentObj, Episode.Episode):
                # ... we can just use the ControlObject's currentObj's object number
                episodeNum = self.currentObj.number
                # If we are at the end of a transcript and there are no later time codes, Stop Time will be -1.
                # This is, of course, incorrect, and we must replace it with the Episode Length.
                if endTime <= 0:
                    endTime = self.currentObj.tape_length
            # If our source is a Clip ...
            elif isinstance(self.currentObj, Clip.Clip):
                # ... we need the ControlObject's currentObj's originating episode number
                episodeNum = self.currentObj.episode_num
                # Sometimes with a clip, we get a startTime of 0 from the TranscriptSelectionInfo() method.
                # This is, of course, incorrect, and we must replace it with the Clip Start Time.
                if startTime == 0:
                    startTime = self.currentObj.clip_start
                # Sometimes with a clip, we get an endTime of 0 from the TranscriptSelectionInfo() method.
                # This is, of course, incorrect, and we must replace it with the Clip Stop Time.
                if endTime <= 0:
                    endTime = self.currentObj.clip_stop
            # We now have enough information to populate a ClipDragDropData object to pass to the Clip Creation method.
            clipData = DragAndDropObjects.ClipDragDropData(transcriptNum, episodeNum, startTime, endTime, text)
            # Pass the accumulated data to the CreateQuickClip method, which is in the DragAndDropObjects module
            # because drag and drop is an alternate way to create a Quick Clip.
            DragAndDropObjects.CreateQuickClip(clipData, nodeParent, nodeName, self.DataWindow.DBTab.tree)
        # If there is something OTHER than a Keyword selected in the Database Tree ...
        else:
            # ... and if we're showing Quick Clip Warnings ...
            if TransanaGlobal.configData.quickClipWarning:
                # ... create an error message
                msg = _("You must select a Keyword in the Data Tree to create a Quick Clip this way.")
                if 'unicode' in wx.PlatformInfo:
                    msg = unicode(msg, 'utf8')
                # Display the error message and then clean up.
                dlg = Dialogs.ErrorDialog(None, msg)
                dlg.ShowModal()
                dlg.Destroy()

        

    def ChangeLanguages(self):
        """ Update all screen components to reflect change in the selected program language """
        self.ClearAllWindows()

        # Let's look at the issue of database encoding.  We only need to do something if the encoding is NOT UTF-8
        # or if we're on Windows single-user version.
        if (TransanaGlobal.encoding != 'utf8') or \
           (('wxMSW' in wx.PlatformInfo) and (TransanaConstants.singleUserVersion)):
            # If it's not UTF-*, then if it is Russian, use KOI8r
            if TransanaGlobal.configData.language == 'ru':
                newEncoding = 'koi8_r'
            # If it's Chinese, use the appropriate Chinese encoding
            elif TransanaGlobal.configData.language == 'zh':
                newEncoding = TransanaConstants.chineseEncoding
            # If it's Eastern European Encoding, use 'iso8859_2'
            elif TransanaGlobal.configData.language == 'easteurope':
                newEncoding = 'iso8859_2'
            # If it's Greek, use 'iso8859_7'
            elif TransanaGlobal.configData.language == 'el':
                newEncoding = 'iso8859_7'
            # If it's Japanese, use cp932
            elif TransanaGlobal.configData.language == 'ja':
                newEncoding = 'cp932'
            # If it's Korean, use cp949
            elif TransanaGlobal.configData.language == 'ko':
                newEncoding = 'cp949'
            # Otherwise, fall back to UTF-8
            else:
                newEncoding = 'utf8'

            # If we're changing encodings, we need to do a little work here!
            if newEncoding != TransanaGlobal.encoding:
                msg = _('Database encoding is changing.  To avoid potential data corruption, \nTransana must close your database before proceeding.')
                tmpDlg = Dialogs.InfoDialog(None, msg)
                tmpDlg.ShowModal()
                tmpDlg.Destroy()

                # We should get a new database.  This call will actually update our encoding if needed!
                self.GetNewDatabase()
                
        self.MenuWindow.ChangeLanguages()
        self.VisualizationWindow.ChangeLanguages()
        self.DataWindow.ChangeLanguages()
        # Updating the Data Window automatically updates the Headers on the Video and Transcript windows!
        for x in range(len(self.TranscriptWindow)):
            self.TranscriptWindow[x].ChangeLanguages()
        # If we're in multi-user mode ...
        if not TransanaConstants.singleUserVersion:
            # We need to update the ChatWindow too
            self.ChatWindow.ChangeLanguages()

    def AdjustIndexes(self, adjustmentAmount):
        """ Adjust Transcript Time Codes by the specified amount """
        self.TranscriptWindow[self.activeTranscript].AdjustIndexes(adjustmentAmount)

    def __repr__(self):
        """ Return a string representation of information about the ControlObject """
        tempstr = "Control Object contents:\nVideoFilename = %s\nVideoStartPoint = %s\nVideoEndPoint = %s\n"  % (self.VideoFilename, self.VideoStartPoint, self.VideoEndPoint)
        tempstr += 'Current open transcripts: %d (%d)\n' % (len(self.TranscriptWindow), self.activeTranscript)
        return tempstr.encode('utf8')

    def _get_activeTranscript(self):
        """ "Getter" for the activeTranscript property """
        # We need to return the activeTranscript value
        return self._activeTranscript

    def _set_activeTranscript(self, transcriptNum):
        """ "Setter" for the activeTranscript property """
        # Initiate exception handling.  (Shutting down Transana generates exceptions here!)
        try:
            # Iterate through the defined Transcript Windows
            for x in range(len(self.TranscriptWindow)):
                # Get the current window title
                title = self.TranscriptWindow[x].dlg.GetTitle()
                # If the current window is NOT the new active trancript, yet is labeled as
                # the active transcript (i.e. is LOSING focus) ...
                if (x != transcriptNum) and (title[:2] == '**') and (title[-2:] == '**'):
                    # ... remove the asterisks from the title.  (CallAfter resolves timing problems)
                    # But skip this if we are shutting down, as trying to set the title of a deleted
                    # window causes an exception!
                    if not self.shuttingDown:
                        wx.CallAfter(self.TranscriptWindow[x].dlg.SetTitle, title[3:-3])
                        
                # If the current window IS the new active transcript, but is not yet labeled
                # as the active transcript (i.e. is GAINING focus) ...
                if (x == transcriptNum) and (title[:2] != '**') and (title[-2:] != '**') and \
                   (len(self.TranscriptWindow) > 1):
                    # ... create a prompt that puts asterisks on either side of the window title ...
                    prompt = '** %s **'
                    if 'unicode' in wx.PlatformInfo:
                        prompt = unicode(prompt, 'utf8')
                    # ... and set the window title to this new prompt
                    self.TranscriptWindow[x].dlg.SetTitle(prompt % title)

                # Set the Menus to match the active transcript's Edit state
                if (x == transcriptNum):
                    # Enable or disable the transcript menu item options
                    self.MenuWindow.SetTranscriptEditOptions(not self.TranscriptWindow[x].dlg.editor.get_read_only())
        except:

            if DEBUG:
                print "Exception in ControlObjectClass._set_activeTranscript()"
            
            # We can ignore it.  This only happens when shutting down Transana.
            pass
        # Set the underlying data value to the new window number
        self._activeTranscript = transcriptNum

    # define the activeTranscript property for the ControlObject.
    # Doing this as a property allows automatic labeling of the active transcript window.
    activeTranscript = property(_get_activeTranscript, _set_activeTranscript, None)