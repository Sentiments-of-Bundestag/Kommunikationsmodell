import re
from pathlib import Path

from bs4 import BeautifulSoup


def main():
    file = Path("/home/rschlett/software_projects/Kommunikationsmodell/18245.xml")
    with file.open("rb") as f:
        soup = BeautifulSoup(f, "xml")

        session_no, legislative_period = [int(p.strip()) for p in soup.NR.getText().split("/")]

        content = soup.TEXT.getText()
        
        start_matcher = re.compile(r"^Beginn:\s\d{1,2}\.\d{2}\sUhr$")
        end_matcher = re.compile(r"^\(Schluss:\s\d{1,2}\.\d{2}\sUhr\)$")

        start_idx = -1
        end_idx = -1
        content_lines = content.split("\n")
        for i, line in enumerate(content_lines):
            if start_idx < 0 and start_matcher.fullmatch(line):
                start_idx = i
            elif end_idx < 0 and end_matcher.fullmatch(line):
                end_idx = i

        rel_lines = content_lines[start_idx + 1:end_idx]

        # todo: there is still a trash line before every "Deutscher Bundestag - ..."
        #  which contains the name of the präsident and needs to be removed.

        # todo: there are also "speeches" which are based on beratungen for
        #  zusatzpunkte -> those need also filtering

        trash_lines = [
            "Deutscher Bundestag – {}. Wahlperiode – {}. Sitzung".format(
                session_no,
                legislative_period),
            "(A) (C)",
            "(B) (D)"]

        def is_a_trash_line(line):
            for tl in trash_lines:
                if line.startswith(tl):
                    return False

            return True

        rel_lines = list(filter(is_a_trash_line, rel_lines))
        
        paras_per_speaker = list()
        curr_para_block = list()
        curr_speaker = ""
        for line in rel_lines:
            if line.endswith(":"):
                line = line.rstrip(":")
                line = line.replace("(", "[")
                line = line.replace(")", "]")
                if curr_para_block:
                    paras_per_speaker.append((curr_speaker, curr_para_block))
                curr_speaker = line
                curr_para_block = list()
            elif curr_speaker:
                curr_para_block.append(line)
            else:
                print("found a paragraph without a speaker!")

        # todo: also the line merging can be improved

        merged_paras_per_speaker = list()
        for speaker, para_lines in paras_per_speaker:
            curr_line = ""
            merged_para_lines = list()
            for line in para_lines:
                if curr_line and line:
                    if curr_line.endswith("-"):
                        curr_line = curr_line.rstrip("-")
                    else:
                        curr_line += " "

                    curr_line += line
                elif curr_line and not line:
                    merged_para_lines.append(curr_line)
                    curr_line = ""
                elif not curr_line and line:
                    curr_line = line

            merged_paras_per_speaker.append((speaker, merged_para_lines))

        print()
        for speaker, para_lines in merged_paras_per_speaker:
            print("During the speech of {} the following paragraphs have been found:".format(speaker))
            print("-" * 80)
            for line in para_lines:
                print(line)
            print()


if __name__ == "__main__":
    main()