# Public starting points. Individual calendars can be substituted in the Sources screen.
COLLEGES = '''All Souls|asc.ox.ac.uk
Balliol|balliol.ox.ac.uk
Brasenose|bnc.ox.ac.uk
Christ Church|chch.ox.ac.uk
Corpus Christi|ccc.ox.ac.uk
Exeter|exeter.ox.ac.uk
Harris Manchester|hmc.ox.ac.uk
Hertford|hertford.ox.ac.uk
Jesus|jesus.ox.ac.uk
Keble|keble.ox.ac.uk
Kellogg|kellogg.ox.ac.uk
Lady Margaret Hall|lmh.ox.ac.uk
Linacre|linacre.ox.ac.uk
Lincoln|lincoln.ox.ac.uk
Magdalen|magd.ox.ac.uk
Mansfield|mansfield.ox.ac.uk
Merton|merton.ox.ac.uk
New College|new.ox.ac.uk
Nuffield|nuffield.ox.ac.uk
Oriel|oriel.ox.ac.uk
Pembroke|pmb.ox.ac.uk
Queen's|queens.ox.ac.uk
Regent's Park|rpc.ox.ac.uk
St Anne's|st-annes.ox.ac.uk
St Antony's|sant.ox.ac.uk
St Catherine's|stcatz.ox.ac.uk
St Cross|stx.ox.ac.uk
St Edmund Hall|seh.ox.ac.uk
St Hilda's|st-hildas.ox.ac.uk
St Hugh's|st-hughs.ox.ac.uk
St John's|sjc.ox.ac.uk
St Peter's|spc.ox.ac.uk
Somerville|some.ox.ac.uk
Trinity|trinity.ox.ac.uk
University College|univ.ox.ac.uk
Wadham|wadham.ox.ac.uk
Wolfson|wolfson.ox.ac.uk
Worcester|worc.ox.ac.uk'''
SOURCES = [
('University of Oxford events','https://www.ox.ac.uk/events','listing'),
('Oxford open days','https://www.ox.ac.uk/about/visit-us/open-days','listing'),
('Oxford Open Doors','https://www.oxfordpreservation.org.uk/oxford-open-doors','listing'),
('Oxford City Council annual events','https://www.oxford.gov.uk/annualevents','listing'),
('Oxford City Council events','https://www.oxford.gov.uk/events-oxford','listing'),
('Oxfordshire large public events and road changes','https://www.oxfordshire.gov.uk/business/licences-and-permits/licences-and-permits/large-public-events','access'),
('Oxford United men home fixtures','https://www.oufc.co.uk/fixture/list/62','fixtures'),
('Oxford University degree ceremonies','https://www.ox.ac.uk/students/graduation/ceremonies','ceremonies'),
('Oxford University term dates','https://www.ox.ac.uk/about/the-university/facts-and-figures/dates-of-term','terms'),
('Oxford Brookes graduation','https://www.brookes.ac.uk/students/graduation','listing'),
('New Theatre Oxford','https://www.atgtickets.com/venues/new-theatre-oxford/whats-on/','theatre'),
('Oxford Playhouse','https://www.oxfordplayhouse.com/','listing'),
('Oxford Town Hall','https://www.oxfordtownhall.co.uk/whats-on/','listing'),
('Oxford Half Marathon','https://oxfordhalf.co.uk/the-run/race-day/','listing'),
('Oxford Pride','https://oxfordpride.uk/pride-events/','listing'),
('May Morning','https://www.oxford.gov.uk/maymorning','listing'),
('Oxford outreach events','https://www.ox.ac.uk/admissions/undergraduate/access-oxford/outreach-events','listing'),
('Oxford Events','https://events.ox.ac.uk/events','listing'),
('Conference Oxford','https://conference-oxford.com/','listing'),
('Oxford Brookes events','https://www.brookes.ac.uk/about-brookes/events','listing'),
('Bodleian Libraries events','https://visit.bodleian.ox.ac.uk/events','listing'),
('Oxford Martin School','https://www.oxfordmartin.ox.ac.uk/events/','listing'),
('Blavatnik School of Government','https://www.bsg.ox.ac.uk/events','listing'),
('Saïd Business School','https://www.sbs.ox.ac.uk/events','listing'),
('Department for Continuing Education','https://www.conted.ox.ac.uk/events','listing'),
('Oxford Internet Institute','https://www.oii.ox.ac.uk/events/','listing'),
('Department of Computer Science','https://www.cs.ox.ac.uk/news/events.html','listing'),
('Department of Physics','https://www.physics.ox.ac.uk/events','listing'),
('Department of Engineering Science','https://eng.ox.ac.uk/events/','listing'),
('Department of Politics and International Relations','https://www.politics.ox.ac.uk/events','listing'),
('Faculty of Law','https://www.law.ox.ac.uk/events','listing'),
('Medical Sciences Division','https://www.medsci.ox.ac.uk/events','listing'),
('Humanities Division','https://www.humanities.ox.ac.uk/events','listing'),
('Social Sciences Division','https://www.socsci.ox.ac.uk/events','listing'),
('Mathematical Institute','https://www.maths.ox.ac.uk/events','listing'),
('Oxford University Museum of Natural History','https://www.oumnh.ox.ac.uk/events','listing'),
('Ashmolean Museum','https://www.ashmolean.org/events','listing'),
('Oxford Botanic Garden and Arboretum','https://www.obga.ox.ac.uk/events','listing'),
('History of Science Museum','https://www.hsm.ox.ac.uk/events','listing'),
('Sheldonian Theatre','https://www.sheldonian.ox.ac.uk/events','listing'),
('Oxford Farming Conference','https://www.ofc.org.uk/conference/2027/delegate_info','major'),
('Oxford Real Farming Conference','https://orfc.org.uk/event/oxford-real-farming-conference-2027/','major'),
('Marmalade Festival and Skoll Forum week','https://www.marmalade.io/','major'),
('Oxford Literary Festival','https://oxfordliteraryfestival.org/','major'),
('IF Oxford Science and Ideas Festival','https://if-oxford.com/events/','science_festival'),
('Oxford International Song Festival','https://oxfordsong.org/','song_festival'),
('Oxford Symposia','https://www.oxfordsymposia.co.uk/event-list','symposia'),
]
SOURCES += [(name if name.endswith('College') else f'{name} College',f'https://www.{host}/events/','listing') for name,host in (line.split('|') for line in COLLEGES.splitlines())]

# Changes to mistaken seed addresses. Only rows still using the original URL are migrated.
SOURCE_URL_FIXES = [
('All Souls College','https://www.all-souls.ox.ac.uk/events/','https://www.asc.ox.ac.uk/events'),
('All Souls College','https://www.asc.ox.ac.uk/events/','https://www.asc.ox.ac.uk/events'),
('Bodleian Libraries events','https://visit.bodleian.ox.ac.uk/events','https://visit.bodleian.ox.ac.uk/events-exhibitions?direct=true'),
('Nuffield College','https://www.nuffield.ox.ac.uk/events/','https://www.nuffield.ox.ac.uk/news-events/events-and-seminars/'),
('Pembroke College','https://www.pmb.ox.ac.uk/events/','https://www.pmb.ox.ac.uk/news-events'),
('Corpus Christi College','https://www.ccc.ox.ac.uk/events/','https://www.ccc.ox.ac.uk/alumni/events-and-reunions'),
('Social Sciences Division','https://www.socsci.ox.ac.uk/events','https://www.socsci.ox.ac.uk/'),
('Oxford Botanic Garden and Arboretum','https://www.obga.ox.ac.uk/events','https://www.obga.ox.ac.uk/whats-on'),
('Faculty of Law','https://www.law.ox.ac.uk/events','https://www.law.ox.ac.uk/content/listing-page/events'),
]
FIXED_URLS = {(name, old): new for name, old, new in SOURCE_URL_FIXES}
SOURCES = [(name, FIXED_URLS.get((name, url), url), kind) for name, url, kind in SOURCES]
