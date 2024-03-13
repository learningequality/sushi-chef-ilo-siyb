#!/usr/bin/env python
import json
import os

import requests
from le_utils.constants.labels import subjects
from ricecooker.chefs import SushiChef
from ricecooker.classes.files import DocumentFile
from ricecooker.classes.files import HTMLZipFile
from ricecooker.classes.licenses import get_license
from ricecooker.classes.nodes import DocumentNode
from ricecooker.classes.nodes import HTML5AppNode
from ricecooker.classes.nodes import TopicNode
from ricecooker.config import LOGGER
from ricecooker.utils.zip import create_predictable_zip

from transform import download_gdrive_files
from transform import prepare_lesson_html5_directory
from transform import unzip_scorm_files

CHANNEL_NAME = "Start and Improve Your Business"
CHANNEL_SOURCE_ID = "ilo-siyb"
SOURCE_DOMAIN = "https://www.ilo.org/empent/areas/start-and-improve-your-business/WCMS_751556/lang--en/index.htm"
CHANNEL_LANGUAGE = "en"
CHANNEL_DESCRIPTION = "The Start and Improve Your Business (SIYB) programme is a management-training programme developed by the International Labour Organization (ILO) with a focus on starting and improving small businesses as a strategy for creating more and better employment for women and men, particularly in emerging economies."
CHANNEL_THUMBNAIL = "chefdata/ilo_siyb.png"
CONTENT_ARCHIVE_VERSION = 1


CHANNEL_LICENSE = get_license(
    "CC BY-SA", copyright_holder="International Labour Organization"
)
SESSION = requests.Session()

categories = [
    subjects.TECHNICAL_AND_VOCATIONAL_TRAINING,
    subjects.ENTREPRENEURSHIP,
    subjects.FINANCIAL_LITERACY,
    subjects.PROFESSIONAL_SKILLS,
    subjects.WORK,
]


class ILOSIYBChef(SushiChef):
    channel_info = {
        "CHANNEL_SOURCE_DOMAIN": SOURCE_DOMAIN,
        "CHANNEL_SOURCE_ID": CHANNEL_SOURCE_ID,
        "CHANNEL_TITLE": CHANNEL_NAME,
        "CHANNEL_LANGUAGE": CHANNEL_LANGUAGE,
        "CHANNEL_THUMBNAIL": CHANNEL_THUMBNAIL,
        "CHANNEL_DESCRIPTION": CHANNEL_DESCRIPTION,
    }

    def download_content(self):
        LOGGER.info("Downloading needed files from Google Drive folders")
        download_gdrive_files()
        LOGGER.info("Uncompressing courses in scorm format")
        unzip_scorm_files()
        # create html5app nodes for each lesson
        for course in self.course_data.keys():
            course_dir = course.replace(" ", "_").lower()
            if course_dir == "training_manuals":
                continue  # skip downloaded pdfs
            for lesson in self.course_data[course]:
                lesson_dir = os.path.join(f"chefdata/{course_dir}/{lesson}")
                if not os.path.exists(lesson_dir):  # create lesson app dir
                    lesson_data = self.course_data[course][lesson]
                    prepare_lesson_html5_directory(lesson_data, lesson_dir)
                LOGGER.info(f"Creating zip for lesson: {lesson} in course {course}")
                self.course_data[course][lesson]["zipfile"] = create_predictable_zip(
                    lesson_dir
                )

    def pre_run(self, args, options):
        self.course_data = json.load(open("chefdata/course_data.json"))
        LOGGER.info("Downloading files from Google Drive folders")

    def construct_channel(self, *args, **kwargs):
        channel = self.get_channel(*args, **kwargs)
        for course in self.course_data.keys():
            course_dir = course.replace(" ", "_").lower()
            thumbnail = (
                f"chefdata/{course_dir}.png"
                if course_dir != "training_manuals"
                else None
            )
            topic_node = TopicNode(
                source_id=f"{course_dir}_id",
                title=course,
                categories=categories,
                derive_thumbnail=True,
                language=CHANNEL_LANGUAGE,
                thumbnail=thumbnail,
                author="International Labour Organization",
            )
            if course_dir != "training_manuals":
                for lesson in self.course_data[course]:
                    lesson_data = self.course_data[course][lesson]
                    zip_file = lesson_data["zipfile"]
                    zip_node = HTML5AppNode(
                        source_id="{}_{}_id".format(
                            course_dir, lesson.replace(" ", "_")
                        ),
                        title=lesson_data["title"],
                        files=[HTMLZipFile(zip_file)],
                        license=CHANNEL_LICENSE,
                        language="en",
                        categories=categories,
                        thumbnail=thumbnail,
                    )
                    topic_node.add_child(zip_node)
            else:
                for chapter in self.course_data[course].keys():
                    chapter_dir = chapter.replace(" ", "_").lower()
                    sub_topic_node = TopicNode(
                        source_id=f"training_manuals_{chapter_dir}_id",
                        title=chapter,
                        categories=categories,
                        derive_thumbnail=True,
                        language=CHANNEL_LANGUAGE,
                        thumbnail=f"chefdata/{chapter_dir}.png",
                        author="International Labour Organization",
                    )
                    for pdf_file in self.course_data[course][chapter]:

                        pdf_info = self.course_data[course][chapter][pdf_file]
                        pdf_node = DocumentNode(
                            source_id="{}_{}_id".format(
                                chapter_dir, pdf_file.replace(" ", "_")
                            ),
                            title=pdf_info["title"],
                            files=[
                                DocumentFile(
                                    f"chefdata/{chapter_dir}/{pdf_info['file']}"
                                )
                            ],
                            license=CHANNEL_LICENSE,
                            language="en",
                            categories=categories,
                        )
                        sub_topic_node.add_child(pdf_node)
                    topic_node.add_child(sub_topic_node)

            channel.add_child(topic_node)
        return channel


if __name__ == "__main__":
    chef = ILOSIYBChef()
    chef.main()
