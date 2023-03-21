import asyncio
import json
import os
import shutil
import sys
import threading
import time

from PyQt5 import QtWidgets, uic, QtCore, QtGui

src_path = '//a44-nas01/Saltpeter/Builds/review'
dest_path = 'D:/builds/'
team = ["Allen.Yang",
        "Ashish.Nagarkoti",
        "Emanuele.Pescatori",
        "Sean.Firman",
        "Marie.Derne"]
ticket = "4AE07A5BA12E3C1D0DE10618ACCDE40B"
url = "https://swarm.a44games.com:2024/api/v9/reviews?change"


class Tool():
    def __init__(self):
        print("Start Tool")
        self.rows = []
        self.username = self.get_username()

    def get_username(self):
        username = self.run_cmd("echo %USERNAME%").strip()
        return username.title()

    def get_change_json(self, change_id):
        change_json = self.run_cmd('curl -s -u "{}:{}" {}={}'.format(self.username, ticket, url, change_id))
        return json.loads(change_json)

    def get_my_changes(self):
        return self.get_user_changes(self.username)

    def get_team_changes(self, progressbar):
        all_changes = []
        team_num = len(team)
        for team_member_id in range(team_num):
            team_member_changes = self.get_user_changes(team[team_member_id])
            all_changes = all_changes + team_member_changes
            percent = int(team_member_id / team_num * 100)
            progressbar.setValue(percent)
        return all_changes

    def get_user_changes(self, user):

        async def make_future(changeID):
            future = loop.run_in_executor(None, self.get_change_json, changeID)
            cmd_json = await future
            changes_json.append(cmd_json)

        changelists = []
        changes_json = []
        command = "p4 changes -s pending -u {}".format(user)
        result = self.run_cmd(command)

        loop = asyncio.get_event_loop()
        tasks = []

        for change in result.splitlines():
            changeID = change.split(" ")[1]
            tasks.append(make_future(changeID))

        loop.run_until_complete(asyncio.wait(tasks))

        for change_json in changes_json:
            change_dic = {}
            lastSeen = change_json["lastSeen"]
            if not lastSeen:
                continue
            if change_json["reviews"][0]["stateLabel"] == "Archived":
                continue

            description = change_json["reviews"][0]["description"]
            stateLabel = change_json["reviews"][0]["stateLabel"]
            testStatus = change_json["reviews"][0]["testStatus"]

            change_dic["changeID"] = str(lastSeen)
            change_dic["user"] = user
            change_dic["description"] = str(description)
            change_dic["stateLabel"] = str(stateLabel)
            change_dic["testStatus"] = str(testStatus)

            changelists.append(change_dic)
            # break
        return changelists

    def tool_clear(self, ui):
        print("clear")

        def deleteItemsOfLayout(layout):
            if layout is not None:
                while layout.count():
                    item = layout.takeAt(0)
                    widget = item.widget()
                    if widget is not None:
                        widget.setParent(None)
                    else:
                        deleteItemsOfLayout(item.layout())

        deleteItemsOfLayout(ui.changeLists_Layout)

    def tool_test(self):
        print("Test")
        t1 = time.time()

        changes = self.get_team_changes()

        t2 = time.time()
        print('程序运行时间为：{:.2f}s'.format(t2 - t1))

    def set_download_status(self, change):
        def get_download_folder_name():
            builds = os.listdir(src_path)
            for i in builds:
                if change["changeID"] in i:
                    return i
            return False

        def downloaded():
            return os.path.exists(os.path.join(dest_path, remote_path))

        change["download_enabled"] = True
        change["download_icon"] = "Download_Green.png"
        remote_path = get_download_folder_name()
        # if has remote path
        if remote_path:
            local_path = downloaded()
            # if has local path
            if local_path:
                change["local_path"] = local_path
                change["download_icon"] = "Folder.png"
                return
            change["remote_path"] = remote_path
            return
        change["download_enabled"] = False

    def get_folder(self, num):
        builds = os.listdir(src_path)
        for i in builds:
            if num in i:
                return i
        if not all_ver:
            return False

    def download(self, change):
        print("download")
        # print(change["change_id"])
        print(change)

    @staticmethod
    def get_change_color(change):
        if change["stateLabel"] == "Approved":
            color = "#00ff00"
        elif change["stateLabel"] == "Needs Revision":
            color = "#ffaa00"
        else:
            color = "#ffffff"
        return color

    @staticmethod
    def run_cmd(command):
        result = os.popen(command).read()
        return result


class Downloader_UI(QtWidgets.QMainWindow, Tool):
    def __init__(self):
        super(Downloader_UI, self).__init__()
        ui_path = "Downloader.ui"
        self.ui = uic.loadUi(ui_path, self)
        self.create_connections()
        self.show()
        self.auto_download = self.ui.checkBox_download.isChecked()
        self.auto_run = self.ui.checkBox_run.isChecked()
        self.progressbar_bottom = self.ui.progressBarBottom
        self.progressbar_bottom.setVisible(False)

    def create_connections(self):
        self.ui.pushButton_showMyChanges.clicked.connect(self.show_my_changes)
        self.ui.pushButton_clear.clicked.connect(self.clear)
        self.ui.pushButton_test.clicked.connect(self.test)

    def show_my_changes(self):
        changes = self.get_my_changes()
        for change in changes:
            self.add_row(change, True, False)

    def clear(self):
        self.tool_clear(self.ui)

    def add_row(self, change, auto_download, auto_run):
        row_layout = QtWidgets.QGridLayout()
        row_layout.change = change
        row_layout.addWidget(self.add_textbox(change["changeID"], change=change), 0, 0, 1, 1)
        row_layout.addWidget(self.add_line(), 0, 1, 1, 1)
        row_layout.addWidget(self.add_textbox(change["user"]), 0, 2, 1, 1)
        row_layout.addWidget(self.add_line(), 0, 3, 1, 1)
        row_layout.addWidget(self.add_description(change["description"]), 0, 4, 1, 1)
        row_layout.addWidget(self.add_line(), 0, 5, 1, 1)

        download_layout = QtWidgets.QHBoxLayout()
        download_layout.addWidget(self.add_checkbox(auto_download, "Auto"))

        self.set_download_status(change)
        download_button = self.add_tool_button(change["download_icon"], 20, 20)
        download_button.clicked.connect(lambda: self.download(change))
        download_button.setEnabled(change["download_enabled"])
        download_layout.addWidget(download_button)

        row_layout.addLayout(download_layout, 0, 6, 1, 1)
        row_layout.addWidget(self.add_line(), 0, 7, 1, 1)

        run_layout = QtWidgets.QHBoxLayout()
        run_layout.addWidget(self.add_checkbox(auto_run, "Auto"))
        run_layout.addWidget(self.add_tool_button("run.png", 20, 20))

        row_layout.addLayout(run_layout, 0, 8, 1, 1)
        row_layout.addWidget(self.add_progressbar(), 1, 0, 1, 9)

        row_layout.addWidget(self.add_line(v=False), 2, 0, 1, 9)
        self.ui.changeLists_Layout.addLayout(row_layout)
        self.rows.append(row_layout)

    def test(self):
        self.progressbar_bottom.setVisible(True)
        self.progressbar_bottom.setValue(0)
        changes = self.get_team_changes(self.progressbar_bottom)
        for i in changes:
            self.add_row(i, True, False)
        self.progressbar_bottom.setVisible(False)

    # make widgets
    @staticmethod
    def add_textbox(text, size=60, change=False):
        textbox = QtWidgets.QLabel()
        textbox.setText(text)
        textbox.setMinimumSize(size, 0)
        textbox.setMaximumSize(size, 5000)
        if change:
            textbox.setText(
                '<a href="https://swarm.a44games.com:2024/reviews/{0}" style="color:{1}; text-decoration: none;">{0}</a>'.format(
                    text, Tool.get_change_color(change)))

            textbox.setTextInteractionFlags(QtCore.Qt.TextBrowserInteraction)

            textbox.setOpenExternalLinks(True)
            textbox.setAlignment(QtCore.Qt.AlignCenter)
        return textbox

    @staticmethod
    def add_line(v=True):
        line = QtWidgets.QFrame()
        if v:
            line.setFrameShape(QtWidgets.QFrame.VLine)
        else:
            line.setFrameShape(QtWidgets.QFrame.HLine)
        line.setFrameShadow(QtWidgets.QFrame.Sunken)
        return line

    @staticmethod
    def add_spacer(v_expanding=True, h_expanding=False):
        v = h = QtWidgets.QSizePolicy.Minimum
        if v_expanding:
            v = QtWidgets.QSizePolicy.Expanding
        if h_expanding:
            h = QtWidgets.QSizePolicy.Expanding
        Spacer = QtWidgets.QSpacerItem(1, 1, v, h)
        return Spacer

    @staticmethod
    def add_description(text):
        description = QtWidgets.QLabel()
        description.setText(text)
        # description.setAlignment(QtCore.Qt.AlignCenter)
        description.setWordWrap(True)
        description.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
        description.setTextFormat(QtCore.Qt.TextFormat.PlainText)
        return description

    @staticmethod
    def add_tool_button(icon_name, width, height, enabled=True):
        button = QtWidgets.QToolButton()
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(icon_name), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        button.setIcon(icon)
        button.setIconSize(QtCore.QSize(width, height))
        button.setMinimumSize(20, 20)
        button.setMaximumSize(20, 20)
        return button

    @staticmethod
    def add_checkbox(value, text=None):
        checkbox = QtWidgets.QCheckBox()
        checkbox.setChecked(value)
        if text:
            checkbox.setText(text)
        return checkbox

    @staticmethod
    def add_progressbar():
        progressbar = QtWidgets.QProgressBar()
        progressbar.setValue(50)
        progressbar.setMaximumSize(1000000, 10)
        progressbar.setVisible(False)
        return progressbar


class thread_copy(threading.Thread):
    def __init__(self, fulldir):
        threading.Thread.__init__(self)
        self.fulldir = fulldir

    def run(self):
        shutil.copytree(os.path.join(src_path, self.fulldir), os.path.join(dest_path, self.fulldir))


app = QtWidgets.QApplication(sys.argv)
window = Downloader_UI()
app.exec_()
