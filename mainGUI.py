import os

import rule34
import gui
import sys
import math
import re
import concurrent.futures
import urllib.request
from timeit import default_timer as timer
from PyQt5 import QtCore, QtGui, QtWidgets

app = QtWidgets.QApplication(sys.argv)
app.setStyle("Fusion")
R34Donwloader = QtWidgets.QMainWindow()
r34 = rule34.Sync()
ui = gui.Ui_Rule34Downloader()

class r34GUI:
    def __init__(self):
        self.searchTerm = None  # The currently entered search term
        self.directory = None  # The save directory
        self.totalExpected = 0  # how many images the program is expecting
        self.imgList = []  # the list that holds images to be downloaded
        self.stopFlag = False  # tells the download thread to stop
        self.done = False  # is the download done?
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)  # the executor for the download thread
        self.dwnTask = None  # the download thread itself


    def main(self):
        # Create the basic ui
        ui.setupUi(R34Donwloader)
        R34Donwloader.resize(500, 450)
        R34Donwloader.show()

        # clear any testing code, and block inputs in the destination line
        ui.searchProgBar.setValue(0)
        ui.destinationLine.setEnabled(False)
        ui.ETA.setText("0 seconds")
        ui.currentTask.setText("Idle")

        # setup events
        ui.browseButton.clicked.connect(self.browse)
        ui.searchButton.clicked.connect(self.search)
        ui.beginButton.clicked.connect(self.begin)
        ui.quitButton.clicked.connect(self._quit)
        ui.cancelButton.clicked.connect(self.cancel)
        ui.ckBoxSaveURLs.clicked.connect(self.checkCanBegin)
        ui.ckboxDownloadImages.clicked.connect(self.checkCanBegin)
        ui.ckBoxDownloadVideos.clicked.connect(self.checkCanBegin)

    def setProgBar(self, value=0):
        """Sets the progress bar percentage, defaults to 0"""
        ui.searchProgBar.setValue(value)

    def toggleUI(self, state: bool):
        """Allows you to disable all input ui, useful when downloading"""
        ui.searchButton.setEnabled(state)
        ui.browseButton.setEnabled(state)
        ui.beginButton.setEnabled(state)
        ui.ckBoxSaveURLs.setEnabled(state)
        ui.ckboxDownloadImages.setEnabled(state)
        ui.ckBoxSubfolder.setEnabled(state)
        ui.ckBoxDownloadVideos.setEnabled(state)
        ui.downloadLimit.setEnabled(state)

    def checkCanBegin(self):
        """Checks if the program has all the information needed to download"""
        print("Checking if able to begin")
        if self.searchTerm is not None and self.directory is not None:
            if ui.ckboxDownloadImages.isChecked() or ui.ckBoxDownloadVideos.isChecked() or ui.ckBoxSaveURLs.isChecked():
                # the program needs something to do, so this assures that there is at least 1 task
                return ui.beginButton.setEnabled(True)
        return ui.beginButton.setEnabled(False)  # disable the begin button

    def browse(self):
        """Sets the download destination"""
        print("Opening browse window")
        ui.currentTask.setText("Waiting for directory")
        self.directory = str(QtWidgets.QFileDialog.getExistingDirectory(R34Donwloader, "Select Directory"))
        ui.destinationLine.setText(self.directory)
        print(f"Destination has been set to {self.directory}")
        self.checkCanBegin()
        ui.currentTask.setText("Idle")


    def search(self):
        """Calls rule34 to search for images with the given tag"""
        ui.currentTask.setText("Searching Rule34")
        self.searchTerm = ui.searchInput.text().replace(",", "")
        print(f"Searching for {self.searchTerm}")
        self.setProgBar(25)
        # technically this call blocks the main thread, but it does it so quickly it really doesnt matter
        self.totalExpected = r34.totalImages(self.searchTerm)
        self.setProgBar(100)
        ui.searchLCD.display(str(self.totalExpected))
        self.checkCanBegin()
        ui.currentTask.setText("Idle")


    def _quit(self):
        """As the name suggests"""
        sys.exit(app.exec_())

    def cancel(self):
        """Clears the app, as if it had just opened
        If a download is currently running, thats stopped too"""
        print("Cancel")
        self.searchTerm = None
        self.directory = None
        self.totalExpected = 0
        self.imgList = []
        self.stopFlag = True
        self.done = False
        self.checkCanBegin()

        try:
            # wait for any download tasks to end
            self.executor.shutdown(wait=True)
            self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        except:
            pass
        self.stopFlag = False

        ui.searchInput.setText(self.searchTerm)
        ui.destinationLine.setText(self.directory)
        ui.searchLCD.display(0)
        ui.ETA.setText("0 seconds")
        ui.currentTask.setText("Cancelled!")
        self.setProgBar()
        self.toggleUI(True)


    def begin(self):
        """Prepares the imagelist and starts the download"""
        print("Begin")
        ui.currentTask.setText("Gathering and validating posts")

        # disable ui so user cant modify anything
        self.toggleUI(False)

        if self.totalExpected == 0:
            self.search()
        estimatedPages = math.ceil(self.totalExpected/100)
        page = 0

        # you could just gather all images at once, but because i want a progress bar, i iterate through the pages myself
        for i in range(estimatedPages):
            self.setProgBar(int((i/estimatedPages)*100))
            newImages = r34.getImages(singlePage=True, OverridePID=i, tags=self.searchTerm)

            # occasionally r34 gives duplicate posts, this catches that
            for image in newImages:
                if any(x.id == image.id for x in self.imgList):
                    newImages.remove(image)
                    print("Removing duplicate")
            self.imgList += newImages

            ui.searchLCD.display(len(self.imgList))
        self.setProgBar(100)

        if ui.downloadLimit.value() != -1:
            self.imgList = self.imgList[:ui.downloadLimit.value()]

        # the download function breaks the ui loop, so i put it in its own thread
        self.dwnTask = self.executor.submit(self._download)
        while not self.done:
            # while waiting for the download, keep the ui active
            app.processEvents()
        self.totalExpected = 0
        self.imgList = []
        self.stopFlag = False
        self.done = False
        ui.ETA.setText("0 seconds")
        ui.currentTask.setText("Download Complete!")
        self.setProgBar(100)
        self.toggleUI(True)

    def _download(self):
        """The downloader itself"""
        ui.currentTask.setText("Downloading")
        directory = self.directory
        if ui.ckBoxSubfolder.isChecked():  # If the user wants a subfolder
            tempTag = re.compile('[^a-zA-Z]').sub('_', self.searchTerm)  # clear non alpha-numeric characters
            newPathName = '_'.join(tempTag.split(" "))  # clear spaces
            directory += f"/{newPathName}"
            if not os.path.isdir(directory):
                print("creating sub-folder")
                os.mkdir(directory)

        numDownloaded = 0
        ETA = 0
        times = []
        urlFileDir = None  # stores the directory of the urlfile, unused
        urlFile = None
        if ui.ckBoxSaveURLs.isChecked():
            # if the user wants urls saved, create the file here
            urlFileDir = f"{directory}/urls.txt"
            urlFile = open(urlFileDir, "w")
            urlFile.write(f"### URLs for search: {self.searchTerm} ###\n")

        for image in self.imgList:
            # ui update
            try:
                average = (sum(times) / len(times))
                ETA = average * (len(self.imgList) - numDownloaded)
            except ZeroDivisionError:
                pass

            ui.searchLCD.display(numDownloaded)
            ui.ETA.setText(f"{round(ETA)} seconds")
            self.setProgBar(int((numDownloaded/len(self.imgList))*100))

            start = timer()
            if self.stopFlag:
                self.stopFlag = False
                if urlFile:
                    urlFile.close()
                self.done = True
                return
            name = "{}/{}.{}".format(directory, image.id.split("/")[-1], image.file_url.split(".")[-1])
            video = ("webm" in name or "mp4" in name)
            try:
                if ui.ckBoxSaveURLs.isChecked():
                    urlFile.write("\n" + image.file_url)
                if ui.ckboxDownloadImages.isChecked() or ui.ckBoxDownloadVideos.isChecked():

                    # allows the user to enable or disable downloads of certain things
                    if video and not ui.ckBoxDownloadVideos.isChecked():
                        continue
                    if not video and not ui.ckboxDownloadImages.isChecked():
                        continue

                    with urllib.request.urlopen(image.file_url) as f:
                        imageContent = f.read()
                        with open(name, "wb") as f:
                            f.write(imageContent)


                numDownloaded += 1
            except Exception as e:
                print(f"Skipping image due to error: {e}")

            end = timer()
            times.append(end - start)
            times = times[-30:]
        if urlFile:
            urlFile.close()

        self.done = True
        return



if __name__ == "__main__":
    _r34GUI = r34GUI()
    try:
        _r34GUI.main()
    except Exception as e:
        print(e)
    sys.exit(app.exec_())
