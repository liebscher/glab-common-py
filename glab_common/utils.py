import scipy.io as sio
import numpy as np
import glob
import pandas as pd
import datetime as dt
import os
import matplotlib.pyplot as plt

def load_mat(filename):
    '''
    this function should be called instead of direct spio.loadmat
    as it cures the problem of not properly recovering python dictionaries
    from mat files. It calls the function check keys to cure all entries
    which are still mat-objects
    '''
    data = sio.loadmat(filename, struct_as_record=False, squeeze_me=True)
    return _check_keys(data)

def _check_keys(dict):
    '''
    checks if entries in dictionary are mat-objects. If yes
    todict is called to change them to nested dictionaries
    '''
    for key in dict:
        if isinstance(dict[key], sio.matlab.mio5_params.mat_struct):
            dict[key] = _todict(dict[key])
    return dict

def _todict(matobj):
    '''
    A recursive function which constructs from matobjects nested dictionaries
    '''
    dict = {}
    for strg in matobj._fieldnames:
        elem = matobj.__dict__[strg]
        if isinstance(elem, sio.matlab.mio5_params.mat_struct):
            dict[strg] = _todict(elem)
        else:
            dict[strg] = elem
    return dict

def load_rDAT(fin,nheaderrows = 0,fmt=None):
    if fmt == None: #replace with your own rdat format
        fmt = [('session','i4'),
               ('trial','i4'),
               ('normal','b'),
               ('stimulus','a64'),
               ('class','i4'),
               ('R_sel','i4'),
               ('R_acc','i4'),
               ('ReactionTime','f4'),
               ('Reinforced','b'),
               ('TimeOfDay','a8'),
               ('Date','a8'),
               ];

    while True:
        if nheaderrows > 100:
            raise ValueError('Recursively found more than 100 header rows.')
        try:
            data = np.genfromtxt(fin,dtype=fmt,invalid_raise=False,skip_header=nheaderrows)
            return data
        except ValueError:
            nheaderrows += 1

def _make_dt_maker(year):
    def dt_maker(x):
        return dt.datetime(year, int(x['old_date'][0:2]), int(x['old_date'][2:]), int(x['TimeOfDay'][0:2]), int(x['TimeOfDay'][2:]))
    return dt_maker

def _read_year_rDAT(rDat_f, nheaderrows):
    with open(rDat_f) as f:
        head = [f.next() for x in xrange(nheaderrows)]
    date_line = filter(lambda x:'Start time' in x, head)
    return int(date_line[0][-5:-1])

def load_data_pandas(subjects, data_folder, force_boolean=['reward']):
    '''
    a function that loads data files for a number of subjects into panda DataFrames.
    supports pyoperant files as well as some c operant data files
        subjects is a tuple of bird ids of any length i.e. ('B999', 'B9999')
        data_folder is the top level folder for the data containing folders matching the elements of subjects
        force_boolean is a list of data entries which will be cast as bool. Can be empty.
    '''
    behav_data = {}
    for subj in subjects:
        df_set = []
        data_files = glob.glob(os.path.join(data_folder,subj,subj+'_trialdata_*.csv'))
        if data_files: # if vogel/pyoperant
            for data_f in data_files:
                with open(data_f,'rb') as f:
                    try:
                        df = pd.read_csv(f,index_col=['time'],parse_dates=['time'])
                        df_set.append(df)
                    except ValueError:
                        df = None
        data_files = glob.glob(os.path.join(data_folder,subj,subj[1:]+'_match2sample*.2ac_rDAT'))
        if data_files:  # if ndege/c operant
            fmt = [('session','i4'),
                   ('trial_number','i4'),
                   ('old_type','b'),
                   ('stimulus','a64'),
                   ('old_class','i4'),
                   ('old_response','i4'),
                   ('old_correct','i4'),
                   ('rt','f4'),
                   ('reinforcement','b'),
                   ('TimeOfDay','a8'),
                   ('old_date','a8'),
                   ];
            for data_f in data_files:
                nheaderrows = 5
                dat = load_rDAT(data_f, nheaderrows=nheaderrows, fmt=fmt)
                
                year = _read_year_rDAT(data_f, nheaderrows)
                df = pd.DataFrame(dat, columns=zip(*fmt)[0])
                dt_maker = _make_dt_maker(year)
                df['date'] = df.apply(dt_maker, axis=1)
                df.set_index('date', inplace=True)
                df['type_'] = df['old_type'].map(lambda(x): ['correction','normal'][x]) 
                df['response'] = df['old_response'].map(lambda(x): ['none', 'L', 'R'][x])
                df['correct'] = df['old_correct'].map(lambda(x): [False, True, float('nan')][x])
                df['reward'] = df.apply(lambda(x): x['reinforcement'] == 1 and x['correct'] == True, axis=1)
                df['class_'] = df['old_class'].map(lambda(x): ['none', 'L', 'R'][x])
                df_set.append(df)
        if df_set:
            behav_data[subj] = pd.concat(df_set)
        else:
            print 'data not found for %s' % (subj)
    if force_boolean:
        for subj in subjects:
            for forced in force_boolean:
                behav_data[subj][forced] = behav_data[subj][forced].map(lambda(x): x in [True, 'True', 'true', 1, '1'])
    return behav_data

## http://stackoverflow.com/questions/13059011/is-there-any-python-function-library-for-calculate-binomial-confidence-intervals
def binP(N, p, x1, x2):
    p = float(p)
    q = p/(1-p)
    k = 0.0
    v = 1.0
    s = 0.0
    tot = 0.0

    while(k<=N):
            tot += v
            if(k >= x1 and k <= x2):
                    s += v
            if(tot > 10**30):
                    s = s/10**30
                    tot = tot/10**30
                    v = v/10**30
            k += 1
            v = v*q*(N+1-k)/k
    return s/tot

def binomial_ci(vx, vN, vCL = 95):
    '''
    Calculate the exact confidence interval for a binomial proportion

    Usage:
    >>> calcBin(13,100)    
    (0.07107391357421874, 0.21204372406005856)
    >>> calcBin(4,7)   
    (0.18405151367187494, 0.9010086059570312)
    ''' 
    vx = float(vx)
    vN = float(vN)
    #Set the confidence bounds
    vTU = (100 - float(vCL))/2
    vTL = vTU

    vP = vx/vN
    if (vx==0):
        dl = 0.0
    else:
        v = vP/2
        vsL = 0
        vsH = vP
        p = vTL/100

        while((vsH-vsL) > 10**-5):
            if(binP(vN, v, vx, vN) > p):
                vsH = v
                v = (vsL+v)/2
            else:
                vsL = v
                v = (v+vsH)/2
        dl = v

    if (vx==vN):
        ul = 1.0
    else:
        v = (1+vP)/2
        vsL =vP
        vsH = 1
        p = vTU/100
        while((vsH-vsL) > 10**-5):
            if(binP(vN, v, 0, vx) < p):
                vsH = v
                v = (vsL+v)/2
            else:
                vsL = v
                v = (v+vsH)/2
        ul = v
    return (dl, ul)

def binomial_ci_array(vx, vN, vCL = 95):
    assert vx.shape == vN.shape
    it = np.nditer([vx, vN, None, None])
    for x, y, dl, ul in it:
        dl[...], ul[...] = binomial_ci(x, y, vCL)
    return (it.operands[2], it.operands[3])

def plot_accuracy(subj, df, blocked_by_day=True, block_size=200):
    data_to_analyze = df[(df.response<>'none')&(df.type_=='normal')&(df.index>(dt.datetime.today()-dt.timedelta(weeks=1)))]
    
    if blocked_by_day:
        blocked = data_to_analyze.groupby(lambda x: (x.date()-dt.datetime.now().date()).days)
    else:
        data_to_analyze = data_to_analyze.reset_index()
        
        blocks = data_to_analyze.index / block_size
        blocked = data_to_analyze.groupby(blocks)
    
    
    correct = blocked['correct'].agg({'correct': lambda x: np.mean(x.astype(float))})
    correct.plot()

    if blocked_by_day:
        days = np.sort(blocked.groups.keys())
        trials_per_day = blocked['response'].count().values
        lci, uci = binomial_ci_array(1.0/2.0*trials_per_day,trials_per_day)
        plt.plot(days, lci, color='grey',alpha=0.5)
        plt.plot(days, uci, color='grey',alpha=0.5)
        plt.xlabel('day')
    else:
        ci = binomial_ci(1.0/2.0*block_size,block_size)
        plt.axhspan(ci[0],ci[1],color='grey',alpha=0.5)
        plt.axhline(1.0/2.0,linestyle=':') 
        plt.xlabel('block')
    
    plt.ylim([0,1.0])
    plt.title(subj)
    plt.ylabel('accuracy')
    
def plot_bias(subj, df, blocked_by_day=True, block_size=200):
    data_to_analyze = df[(df.response<>'none')&(df.type_=='normal')&(df.index>(dt.datetime.today()-dt.timedelta(weeks=1)))]
    
    if blocked_by_day:
        blocked = data_to_analyze.groupby(lambda x: (x.date()-dt.datetime.now().date()).days)
        days = np.sort(blocked.groups.keys())
        trials_per_day = blocked['response'].count().values
        lci, uci = binomial_ci_array(1.0/2.0*trials_per_day,trials_per_day)
    else:
        ci = binomial_ci(1.0/2.0*block_size,block_size)
        data_to_analyze = data_to_analyze.reset_index()
        
        blocks = data_to_analyze.index / block_size
        blocked = data_to_analyze.groupby(blocks)
    
    response_set = set(['R','L','C']).intersection(set(df['response']))
    # Definitely bad form, do not use where there is a possibility of hacking
    def bias_maker(response):
        import numpy as np
        exec """def %s_bias(x):
            return np.mean((x=="%s").astype(float))""" % (response, response) in locals()
        return eval("%s_bias" % (response))

    bias_funcs = [bias_maker(resp) for resp in response_set]
    bias = blocked['response'].agg(bias_funcs)
    bias.plot()

    if blocked_by_day:
        plt.plot(days, lci, color='grey',alpha=0.5)
        plt.plot(days, uci, color='grey',alpha=0.5)
        plt.xlabel('day')
    else:
        plt.axhspan(ci[0],ci[1],color='grey',alpha=0.5)
        plt.axhline(1.0/2.0,linestyle=':') 
        plt.xlabel('block')


    plt.ylim([0,1.0])
    plt.title(subj)
    plt.ylabel('bias')

def vinjegallant(response):

    R = np.asarray(response[:])
    n = np.float_(len(R))
    eps = spacing(np.float64(1))

    A = ((R.sum()/n)**2) / (((R**2).sum()/n) + eps)
    S = (1 - A) / (1 - 1/n)
    
    return S


#perc corr broken out by stimulus and day. input how many days you want to look at into "days" argument
#stims_all is a list of all stimuli in the order you want them displayed
def accperstimplot(subj,df,days=7,stims_all=None):
    data_to_analyze = df[(df.response!='none')&(df.type_=='normal')&(df.index>(dt.datetime.today()-dt.timedelta(days=days)))]
    #get any stims that have been shown to bird
    if not stims_all:
        stims_all = sorted(list(set(data_to_analyze.stimulus)))
    #stims = list(set(data_day.stimulus))
    blocked = data_to_analyze.groupby([lambda x: (dt.datetime.now().date()-x.date()).days, data_to_analyze.stimulus])
    aggregated = blocked.agg({'correct': lambda x: np.mean(x.astype(float))})
    days_passed = np.arange(days)
    stim_number = np.arange(len(stims_all))
    
    plt.figure()
    plt.subplot(1,2,2)
    cmap = plt.get_cmap('Oranges')
    cmap.set_bad(color = 'k', alpha = 0.5)
    correct = np.zeros((len(days_passed),len(stim_number)),np.float_)
    
    for day in days_passed:
        for st in stim_number:
            try:
                correct[day,st] = aggregated['correct'][day,str(stims_all[st])]
            except KeyError:
                correct[day,st] = np.nan
    correct = np.ma.masked_invalid(correct)
    plt.pcolormesh(np.rot90(np.fliplr(correct),k=3),cmap=cmap,vmin=0, vmax=1)
    plt.colorbar()
    plt.title(subj)
    plt.xlabel('day')
    plt.ylabel('stim')
