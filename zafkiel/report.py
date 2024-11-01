import os
import shutil
import traceback

from PIL import Image
from airtest.aircv import imread, FileNotExistError, get_resolution

from airtest.report.report import LogToHtml, LOGGING, HTML_FILE, DEFAULT_LOG_DIR, DEFAULT_LOG_FILE, HTML_TPL
from airtest.utils.compat import script_dir_name
from airtest.utils.logwraper import AirtestLogger

from zafkiel.config import Config


class ZafkielLogger(AirtestLogger):
    # Changed file mode from "w" to "a" to append to the log file instead of overwriting it.
    def set_logfile(self, logfile):
        if logfile:
            self.logfile = os.path.realpath(logfile)
            self.logfd = open(self.logfile, "a")
        else:
            # use G.LOGGER.set_logfile(None) to reset logfile
            self.logfile = None
            if self.logfd:
                self.logfd.close()
                self.logfd = None


class HtmlReport(LogToHtml):
    @classmethod
    def get_thumbnail(cls, path):
        """compress screenshot"""
        new_path = cls.get_small_name(path)
        if not os.path.isfile(new_path):
            try:
                img = Image.open(path)
                compress_image(img, new_path, Config.ST.SNAPSHOT_QUALITY, max_size=300)
            except:
                LOGGING.error(traceback.format_exc())
            return new_path
        else:
            return None

    def _translate_code(self, step):
        if step["tag"] != "function":
            return None
        step_data = step["data"]
        args = []
        code = {
            "name": step_data["name"],
            "args": args,
        }
        for key, value in step_data["call_args"].items():
            args.append({
                "key": key,
                "value": value,
            })
        for k, arg in enumerate(args):
            value = arg["value"]
            if isinstance(value, dict) and value.get("__class__") == "ImageTemplate":
                if self.export_dir:  # all relative path
                    image_path = value['filename']
                    if not os.path.isfile(os.path.join(self.script_root, image_path)) and value['_filepath']:
                        # copy image used by using statement
                        shutil.copyfile(value['_filepath'], os.path.join(self.script_root, value['filename']))
                else:
                    image_path = os.path.abspath(value['_filepath'] or value['filename'])
                arg["image"] = image_path
                try:
                    if not value['_filepath'] and not os.path.exists(value['filename']):
                        crop_img = imread(os.path.join(self.script_root, value['filename']))
                    else:
                        crop_img = imread(value['_filepath'] or value['filename'])
                except FileNotExistError:
                    # 在某些情况下会报图片不存在的错误（偶现），但不应该影响主流程
                    if os.path.exists(image_path):
                        arg["resolution"] = get_resolution(imread(image_path))
                    else:
                        arg["resolution"] = (0, 0)
                else:
                    arg["resolution"] = get_resolution(crop_img)
        return code


def compress_image(pil_img, path, quality, max_size=None):
    """
    Save the picture and compress

    :param pil_img: PIL image
    :param path: save path
    :param quality: the image quality, integer in range [1, 99]
    :param max_size: the maximum size of the picture, e.g 1200
    :return:
    """
    if max_size:
        # The picture will be saved in a size <= max_size*max_size
        pil_img.thumbnail((max_size, max_size), Image.LANCZOS)
    quality = int(round(quality))
    if quality <= 0 or quality >= 100:
        raise Exception("SNAPSHOT_QUALITY (" + str(quality) + ") should be an integer in the range [1,99]")
    pil_img.save(path, quality=quality, optimize=True)


def simple_report(filepath, log_path=True, logfile=None, output=HTML_FILE):
    path, name = script_dir_name(filepath)
    if log_path is True:
        log_path = os.path.join(path, getattr(Config.ST, "LOG_DIR", DEFAULT_LOG_DIR))
    rpt = HtmlReport(path, log_path, logfile=logfile or getattr(Config, "LOG_FILE", DEFAULT_LOG_FILE), script_name=name)
    rpt.report(HTML_TPL, output_file=output)
