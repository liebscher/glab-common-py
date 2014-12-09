Gentner Lab Common
====================

shared code for common lab functions, analyses, etc

currently implemented functions:

* utils.load_mat - improved loading of *.mat files so that matlab structs are maintained as python dicts
* utils.load_rDAT - imports rDAT files (from old 'c' behavior scripts) into a numpy.recarray, ignoring header rows and playwav errors

## Klustakwik helper scripts

There are two scripts which will get your data from [probe-the-broab](https://github.com/gentnerlab/probe-the-broab) into the KWD format that KlustaKwik requires. These are assuming you are working on lintu, where a common klustakwik installation is running for the lab to use.

### Determine which Epoch files to compile for spike sorting

1. From a single Site directory, run `make_s2mat_list`. This will generate a text file (`files_to_compile.txt`) in the site directory listing all of the .mat files exported from Spike2 by `probe-the-broab`.
2. Edit `files_to_compile.txt` and delete any epoch files which you do not wish to sort (e.g. data from searching)
3. (Optional) Rename `files_to_compile.txt` if you want to test multiple compilations.

### Compile probe-the-broab mat files into a single KWD file

1. From the site directory, run `s2mat_to_kwd {files_to_compile.txt ProbeName}` e.g. `s2mat_to_kwd files_to_compile.txt A1x16-5mm50`
2. (optional) Edit the generated `.prm` file to tweak any parameters
3. Copy the necessary probe file into the Site directory (TODO: do this in the script)
4. `source activate klusta` to enter into the klustakwik conda environment
4. `klusta` will run spike detection and clustering
5. `klustaviewa` will launch the GUI to combine and rate clusters. [The DeWeese Lab has a nice HowTo for this final part of spike sorting](http://deweeselab.berkeley.edu/Home/research-interests/spike-sorting).

