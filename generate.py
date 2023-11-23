import os
from jinja2 import Template, Environment, FileSystemLoader
#from LoadPage import get_image_name

# Render html file
env = Environment(loader=FileSystemLoader('templates'))
#template = env.get_template('chapter.jinja')
index_template = env.get_template('index.jinja')


#class HtmlImage:
#    def __init__(self, name:str, chapter:str):
#        self.name = name
#        self.chapter = chapter
#        self.change_extention()
#        self.path = self.get_image_path()
#
#    def get_image_path(self):
#        path = "../images/chapter_" + self.chapter + "/" + self.name
#        return path
#
#    def change_extention(self):
#        self.name = self.name[:-4] + ".jpg"
#
#    def __str__(self):
#        return self.path
#
#
#class HtmlChapter:
#    def __init__(self, chapter: str):
#        self.chapter = chapter
#        self.path = self.get_chapter_path()
#
#    def get_chapter_path(self):
#        path = "chapters/index_" + self.chapter + ".html"
#        return path
#
#    def __str__(self):
#        return self.path
#
#
#def sort_by_chapter(html_chapter: HtmlChapter):
#    if "-" in html_chapter.chapter:
#        result = ".".join(html_chapter.chapter.split("-"))
#    else:
#        result = html_chapter.chapter
#    return float(result)
#
#
#def get_image_list():
#    for i in range(121, 122):
#        folder_name = "images_" + str(i)
#
#
#def load_chapter_images(chapter):
#    chapter_file = "chapter_links/chapter_" + str(chapter) + ".txt"
#    images = []
#    with open(chapter_file, "r") as read_file:
#        for line in read_file:
#            line = line.strip()
#            name = get_image_name(line)
#            img = HtmlImage(name, chapter)
#            images.append(img)
#    return images
#
#
#def create_chapter_files():
#    chapters = []
#    for file in os.listdir("./chapter_links"):
#        if file.endswith(".txt"):
#            chapter_name = file[8:-4]
#            chapter = HtmlChapter(chapter_name)
#            chapters.append(chapter)
#            images = load_chapter_images(chapter_name)
#            chapter_page_name = "site/chapters/index_{}.html".format(chapter_name)
#            chapter_title = "Chapter {}".format(chapter_name)
#            output_from_parsed_template = template.render(images=images, chapter_title=chapter_title)
#            with open(chapter_page_name, "w") as chap_page:
#                chap_page.write(output_from_parsed_template)
#            print("Generated : ", chapter_page_name)
#
#    return chapters


def main():
    #chapters = create_chapter_files()
    #chapters.sort(key=sort_by_chapter)

    #output_from_parsed_template = index_template.render(chapters=chapters, total=len(chapters))
    output_from_parsed_template = index_template.render()
    with open("public/index.html", "w") as f:
        f.write(output_from_parsed_template)

    print("Generated : ", "public/index.html")


if __name__ == '__main__':
    main()
