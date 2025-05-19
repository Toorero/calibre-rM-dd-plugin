# SPDX-License-Identifier: EUPL-1.2

from calibre.devices.interface import DevicePlugin, BookList
from calibre.devices.errors import FreeSpaceError
import calibre_plugins.remarkable_rmapi_plugin.config

import shutil
import subprocess
import os.path
import sys
import re
import tempfile
from pathlib import Path

from dataclasses import dataclass, field
from typing import List


class ReMarkablePlugin(DevicePlugin):
    name = "reMarkable Device Plugin"
    description = "Send files to your reMarkable by using rmapi"
    author = "Julius Rüberg"
    supported_platforms = ["linux"]
    version = (1, 2, 3)  # The version number of this plugin
    minimum_calibre_version = (0, 7, 53)

    rmapi_path = config.prefs["rmapi"]
    export_path = config.prefs["export_path"]

    FORMATS = ["epub", "pdf"]

    MANAGES_DEVICE_PRESENCE = True

    def __init__(self, plugin_path):
        DevicePlugin.__init__(self, plugin_path)

        self.seen_device = False

        self.device_total_space = -1
        self.device_free_space = -1

        self.device_name = "rMAPI"
        self.device_version = 2
        self.device_software_version = -1

        self.booklist = ReMarkableBookList(None, "", None)

    def startup(self):
        sys.path.append(self.plugin_path)
        self.working_dir = tempfile.mkdtemp(prefix="calibre_rM_dd")

    def is_customizable(self):
        return True

    def detect_managed_devices(self, devices_on_system, force_refresh=False):
        if self.seen_device:
            return True

        print(f"rmapi binary detected at {self.rmapi_path}")
        print("Probing rmapi to check if it's setup correctly...")
        res = subprocess.Popen(
            [self.rmapi_path, "-ni", "account"], stdout=subprocess.PIPE
        )
        res.wait(1000)
        if res.returncode == 0:
            print("rmapi configured correctly")
            print("Device detected")

            matched = re.match(
                r".+SyncVersion: (\d+)", res.stdout.read().decode("utf-8")
            )
            if matched:
                self.device_software_version = matched.group(1)
            return True
        else:
            print("rmapi not configured, try to run `rmapi`")

    print("No Device detected")

    def debug_managed_device_detection(self, devices_on_system, output):
        # todo implement debug_managed_device_detection
        print("Debug not supported")

    def can_handle_windows(self, usbdevice, debug=False):
        return debug

    def open(self, connected_device, library_uuid):
        print("Opening reMarkable device")
        # try obtaining some device information if connection via SSH is possible
        self._rm_invoke_df()

        # todo support multilevel export paths like 'calibre/export/here' by emulating `mkdir -p`
        # create export directory
        subprocess.call([self.rmapi_path, "mkdir", self.export_path])

    def eject(self):
        # nothing to do here really
        self.seen_device = False

    def post_yank_cleanup(self):
        self.eject()

    def stop_plugin(self):
        self.eject()

    def shutdown(self):
        self.eject()
        shutil.rmtree(self.working_dir, ignore_errors=True)

    def set_progress_reporter(self, report_progress):
        pass

    def get_device_information(self, end_session=True):
        return (
            self.device_name,
            self.device_version,
            self.device_software_version,
            "TODO",
        )

    def get_deviceinfo(self):
        self.get_device_information()

    def card_prefix(self, end_session=True):
        return None, None

    def total_space(self, end_session=True):
        return self.device_total_space, 0, 0

    def free_space(self, end_session=True):
        return self.device_free_space, -1, -1

    def books(self, oncard=None, end_session=True):
        if oncard:
            return []
        return self.booklist

    def upload_books(self, files, names, on_card=None, end_session=True, metadata=None):
        print(f"Uploading {len(files)} books")
        locations = []

        for i in range(0, len(files)):
            file = files[i]
            basename = os.path.basename(file)
            if metadata:
                name = metadata[i].get("title")
            else:
                name = names[i]

            size = os.path.getsize(file)
            if (
                self.device_free_space + size > self.device_total_space
                and self.device_free_space >= 0
            ):
                raise FreeSpaceError("No space left in device 'memory'")
            elif self.device_free_space >= 0:
                self.device_free_space -= size

            ret = subprocess.call([self.rmapi_path, "put", file, self.export_path])
            if ret != 0:
                print(f"Uploading of {file} was unsuccessful")
                continue
            print(f"Uploaded {file}")
            remote_file = f"{self.export_path}/{os.path.splitext(basename)[0]}"
            remote_named_file = f"{self.export_path}/{name}"

            # mv file to rename if necessary
            if basename != name:
                ret = subprocess.call(
                    [self.rmapi_path, "mv", remote_file, remote_named_file]
                )
                if ret != 0:
                    print(
                        f"Renaming of uploaded file {file} was unsuccessful: From: {
                            remote_file
                        } to {remote_named_file}"
                    )
                else:
                    remote_file = remote_named_file

            locations += remote_file

        print("Finished uploading books")
        return locations, metadata, self.booklist

    @classmethod
    def add_books_to_metadata(cls, locations, metadata, booklists):
        print("Adding books to metadata")
        print(f"locations: {locations}, metadata: {metadata}, booklists: {booklists}")
        for i, m in enumerate(metadata):
            title = m.get("title")
            authors = m.get("authors")
            tags = m.get("tags")
            pubdate = m.get("pubdate")
            size = m.get("size")
            uuid = m.get("uuid")
            path = locations[0][i]
            b = RemarkableBook(
                title=title,
                authors=authors,
                size=size,
                datetime=pubdate.timetuple(),
                tags=tags,
                uuid=uuid,
                path=path,
            )
            if b not in booklists[0]:
                booklists[0].add_book(b, None)

    def delete_books(self, paths, end_session=True):
        print(f"Deleting {len(paths)} books")

        for path in paths:
            # todo check if path is really remote-path
            ret = subprocess.call([self.rmapi_path, "rm", path])
            if ret != 0:
                print(f"Deleting of {path} was unsuccessful")
                continue

            if self.device_free_space >= 0:
                # todo adjust size
                pass

        print("Finished deleting books")

    @classmethod
    def remove_books_from_metadata(cls, paths, booklists):
        to_remove = []
        for book in booklists[0]:
            if book.path in paths:
                to_remove.append(book)

        for book in to_remove:
            booklists[0].remove_book(book)

    def sync_booklists(self, booklists, end_session=True):
        # todo implement
        pass

    def get_file(self, path: Path, outfile, end_session=True):
        # try to export annotation but if we're unable for some reason, skip annotations
        if (
            subprocess.call([self.rmapi_path, "geta", path], cwd=self.working_dir) != 0
            or subprocess.call([self.rmapi_path, "get", path], cwd=self.working_dir)
            != 0
        ):
            return

        with open(Path(self.working_dir) / os.path.basename(path), "r") as f:
            for line in f:
                outfile.write(line)

    @classmethod
    def config_widget(cls):
        return config.ConfigWidget()

    @classmethod
    def save_settings(cls, settings_widget):
        settings_widget.save_settings()
        cls.rmapi_path = config.prefs["rmapi"]
        cls.export_path = config.prefs["export_path"]

    @classmethod
    def settings(cls):
        return Opts(cls.FORMATS)

    def _rm_invoke_df(self):
        # todo make configurable
        cmd = "ssh reMarkable df .local/share/remarkable/xochitl/"
        df_res = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
        df_res.wait(1000)
        if df_res.returncode != 0:
            self.device_free_space = -1
        else:
            lines = df_res.stdout.read().decode("utf-8").split("\n")
            df_matching = re.match(
                r"(/.+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(.+)\s+(/.+)", lines[1]
            )
            if df_matching:
                self.device_total_space = int(df_matching.group(2)) * 1024
                self.device_free_space = int(df_matching.group(4)) * 1024

    def _query_rmapi_info(self):
        rmapi_acc = subprocess.Popen(
            [self.rmapi_path, "account"], stdout=subprocess.PIPE
        )


class ReMarkableBookList(BookList):
    def __init__(self, oncard, prefix, settings):
        pass

    def supports_collections(self):
        return False

    def add_book(self, book, replace_metadata=None):
        self.append(book)

    def remove_book(self, book):
        self.remove(book)

    def get_collections(self, collection_attributes):
        return self


@dataclass()
class RemarkableBook:
    title: str
    authors: List[str]
    size: int
    datetime: field(init=False)
    tags: List[str]
    uuid: str
    path: str
    thumbnail: str = ""

    def __eq__(self, other):
        return self.uuid == other.uuid


class Opts:
    def __init__(self, format_map):
        self.format_map = format_map
