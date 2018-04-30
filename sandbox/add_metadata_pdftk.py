import subprocess

PDFTK_PATH = 'C:\\Program Files (x86)\\PDFtk\\bin\\pdftk.exe'
KEY_VALUE_PATTERN = 'InfoBegin\nInfoKey: {}\nInfoValue: {}\n'


if __name__ == '__main__':
    input_path = 'C:\\Users\sbrisard\\MyCoRe\\biblio\\a\\arbi2018\\arbi2018.pdf'
    output_path = 'C:\\Users\\sbrisard\\Documents\\professionnels\\tmp'

    title = 'Tintin'
    author = 'Hergé'

    with open('metadata.pdftk', mode='w', encoding='utf8') as f:
        f.write(KEY_VALUE_PATTERN.format('Title', 'Tintin'))
        f.write(KEY_VALUE_PATTERN.format('Author', 'Hergé'))

        subprocess.run([PDFTK_PATH, input_path,
                        'update_info_utf8', f.name,
                        'output', 'test.pdf'])
