"""
Name: Rule34 Downloader
Author: Daniel Allen -- LordOfPolls - https://github.com/LordOfPolls
Version: 0.1.0
Date: 18/07/2019
"""
import rule34
import time
import os
import sys
import subprocess
from timeit import default_timer as timer
import urllib.request
import tkinter as tk
import re
from tkinter import filedialog

root = tk.Tk()
root.withdraw()
Rule34 = rule34.Sync()

class Downloader:
    def __init__(self):
        self.downloading = False  # Are we downloading right now?
        self.empty = True  # Is the queue of files empty?
        self.connection = False  # Do we have an internet connection
        self.webm = False
        self.silent = False  # Run the script silently
        self.debug = False
        self.downloadLocation = None
        self.tags = ""
        self.errors = []  # list of errors used when downloading
        self.limit = 0  # Limits how many images to download

        self.commandLineParse()  # process command line args if any
        self.checkConnection()  # validate that we have an internet connection

    def debugPrint(self, string):
        if self.debug:
            print(string)

    def commandLineParse(self):
        # todo: Parse command line arguments
        return None

    def generateProgBar(self, numDownloaded, toDownload):
        prog_bar_str = ''
        progress_bar = 27
        percentage = numDownloaded / toDownload

        for i in range(progress_bar):
            if (percentage < 1 / progress_bar * i):
                prog_bar_str += '='
            else:
                prog_bar_str += u'█'
        return prog_bar_str

    def response(self, prompt):
        """Wrapper for input() allowing the result to be normalised to a boolean"""
        prompt += " (y/n) "
        for i in range(3):
            resp = input(prompt).lower()
            if "y" in resp:
                return True
            elif "n" in resp:
                return False
            else:
                print("Invalid response")
        print("Too many invalid responses, quiting")
        time.sleep(1)
        exit(0)

    @staticmethod
    def open(path):
        """Calls the appropriate command to open a path on windows, mac, and unix"""
        if sys.platform == "win32":
            os.startfile(path)
        else:
            command = "open" if sys.platform == "darwin" else "xdg-open"
            subprocess.call([command, path])

    @staticmethod
    def clear():
        if sys.platform == "win32":
            os.system("cls")
        else:
            os.system("clear")

    def checkConnection(self):
        try:
            self.debugPrint("Checking Rule34 for response")
            urllib.request.urlopen('https://rule34.xxx/', timeout=1)  # Check rule34 for a response
            self.debugPrint("Rule34 responded")
            self.connection = True
        except urllib.request.URLError as err:
            self.connection = False

    def download(self, images):
        times = []
        self.debugPrint("Sorting list...")
        webmList = []
        try:
            for image in images:
                if "webm" in image.id:
                    if self.webm:
                        webmList.append(image)
                    images.remove(image)
        except AttributeError:
            print("Your version of rule34 API is out of date, please update it")
            time.sleep(5)
            exit()
        for video in webmList:
            images.append(video)
        if self.response("Create new folder?"):
            tempTag = re.compile('[^a-zA-Z]').sub('_', self.tags)

            newPathName = '_'.join(tempTag.split(" "))
            newPathName = '/'.join([self.downloadLocation, newPathName])
            if not os.path.isdir(newPathName):
                os.mkdir(newPathName)
        else:
            newPathName = self.downloadLocation

        numDownloaded = 0
        print("Downloaded {}/{}".format(numDownloaded, len(images)))
        average = 0
        ETA = 0
        for image in images:
            try:
                name = "{}/{}.{}".format(newPathName, image.id.split("/")[-1], image.file_url.split(".")[-1])

                statusString = """Downloading {Downloaded}/{ToDownload}
File name: {name}
Average Time: {average:.3g} seconds
ETA: {ETA} seconds
{ProgBar}

{Errors}
                """.format(Downloaded=numDownloaded, ToDownload=len(images),
                           name=name.replace(self.downloadLocation, self.downloadLocation.split("/")[-1]),
                           average=average, ETA=round(ETA), ProgBar=self.generateProgBar(numDownloaded, len(images)),
                           Errors='\n'.join(self.errors))
                self.clear()
                print(statusString)
                if os.path.isfile(name):
                    print(image, "Already exists")
                    images.remove(image)
                else:
                    if "webm" in name:
                        print("Downloading webms... this will take longer")
                    start = timer()
                    with urllib.request.urlopen(image.file_url, ) as f:
                        imageContent = f.read()
                        with open(name, "wb") as f:
                            f.write(imageContent)
                        numDownloaded = numDownloaded + 1
                        end = timer()
                        times.append(end - start)
                        times = times[-30:]
                        average = (sum(times) / len(times))
                        ETA = average * (len(images) - numDownloaded)

            except Exception as e:
                self.errors.append("Skipped {} due to: {}".format(image.id.split("/")[-1], e))
                images.remove(image)

        self.open(self.downloadLocation)

    def menu(self):
        if not self.connection:
            print("Error: Unable to connect to Rule34, quiting")
            time.sleep(10)
            exit(1)

        self.tags = input("Search Term: ")
        self.debugPrint("Querying Rule34...")
        totalImages = Rule34.totalImages(self.tags)

        if totalImages > 0:
            print("{} images expected!".format(totalImages))
            if self.response("Would you like to download?"):
                if self.response("Would you like to download videos too?"):
                    self.webm = True

                if self.response("Would you like to limit how many images are downloaded?"):
                    try:
                        self.limit = int(input("Image Limit: "))

                    except ValueError:
                        print("Error, integer expected, try again")
                else:
                    self.limit = totalImages
                file_path = None
                for i in range(3):
                    file_path = filedialog.askdirectory(title="Download location", mustexist=True)
                    if file_path is None or file_path == "":
                        print("No download location specified")
                    else:
                        break
                if file_path is None:
                    exit(1)
                self.downloadLocation = file_path
                print("Gathering Data from rule34, this is predicted to take {0:.3g} seconds".format(0.002*totalImages))
                start = timer()
                images = Rule34.getImages(self.tags, singlePage=False)
                images = images[:self.limit]
                end = timer()
                total = end-start
                print(total/totalImages)
                if images is None:
                    print("No images found... this shouldnt happen")
                else:
                    print("Download commencing")
                    self.download(images)
        else:
            print("No images found")
            time.sleep(1)
            self.menu()

        self.debugPrint("EOF")
        return True


if __name__ == "__main__":
    main = Downloader()
    main.menu()
