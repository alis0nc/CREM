"""
Inserts data into the CREM database.
"""

import sys
import os
import unicodecsv as csv
import datetime

from app import app, db
from app.models import Convention, Timeslot, Track, Event, Presenter
from app.models import Room, RoomGroup, DataLoadError

CONVENTION_INFO_FNAME = 'convention_info.csv'


def get_timeslots(start_date_str, start_time_str, end_date_str, end_time_str,
                  convention, Timeslot):
    """
    Given a start date and time and end date and time for an event, return a
    list of timeslots. Dates have the format "mm/dd/yyyy" and times have the
    format "hh:mm" in 24-hour time.
    """
    # The list of timeslots to return.
    timeslots = []

    # Create datetime object for the start and end of the event.
    event_start_dt = datetime.datetime.strptime('%s %s' % (start_date_str, start_time_str),
                                                '%m/%d/%y %H:%M')

    event_end_dt = datetime.datetime.strptime('%s %s' % (start_date_str, start_time_str),
                                              '%m/%d/%y %H:%M')

    # Calculate the length of each timeslot in seconds.
    num_timeslot_seconds = convention.timeslot_duration.total_seconds()

    # Calculation the number of timeslots for this event.
    num_event_seconds = (event_end_dt - event_start_dt).total_seconds()
    num_timeslots = num_event_seconds//num_timeslot_seconds + 1

    # Determine the index of the first timeslot of the event.
    num_seconds_since_conv_start = (event_start_dt - convention.start_dt).total_seconds()
    if num_seconds_since_conv_start < 0:
        raise Exception('Error: event occurs before start of convention')
    first_index = num_seconds_since_conv_start/num_timeslot_seconds

    # Add timeslots to the list.
    timeslot_indexes = list(range(int(first_index), int(first_index) + int(num_timeslots)))
    for timeslot_index in timeslot_indexes:
        timeslot = Timeslot.query.filter_by(timeslot_index=timeslot_index).first()
        timeslots.append(timeslot)

    return timeslots


def refresh_data(sched_info_fname, convention_info_fname=None):
    # Keep track of the number of errors and warnings.
    num_errors = 0
    num_warnings = 0

    # Delete records from tables of interest.
    events = Event.query.all()
    for event in events:
        event.rooms = []
        event.presenters = []
        event.timeslots = []
    db.session.commit()

    DataLoadError.query.delete()
    Convention.query.delete()
    Timeslot.query.delete()
    Track.query.delete()
    Event.query.delete()
    Presenter.query.delete()
    Room.query.delete()
    RoomGroup.query.delete()

    # Define the convention.

    if not convention_info_fname:
        script_dir = os.path.dirname(__file__)
        convention_info_fname = os.path.join(script_dir, CONVENTION_INFO_FNAME)

    convention = Convention()
    with open(convention_info_fname, 'rb') as csvfile:
        csvreader = csv.reader(csvfile, delimiter=',', quotechar='"')
        first_row = True
        for row in csvreader:
            if first_row:
                first_row = False
            else:
                convention.name = row[0]
                convention.description = row[1]
                convention.date_format = row[5]
                convention.datetime_format = row[6]
                convention.start_dt = datetime.datetime.strptime(row[2], convention.datetime_format)
                convention.end_dt = datetime.datetime.strptime(row[3], convention.datetime_format)
                convention.timeslot_duration = datetime.timedelta(0, int(row[4])*60) # Minutes converted to seconds.
                convention.url = row[7]
                convention.active = True

                # There is only one row of convention data.
                break
    db.session.add(convention)
    db.session.commit()

    # Commit the data to the database.
    db.session.commit()

    # Create timeslots.
    timeslot_count = int((convention.end_dt - convention.start_dt).total_seconds() /
                         convention.timeslot_duration.total_seconds())
    for n in range(timeslot_count):
        timeslot = Timeslot(n)
        timeslot.active = True
        db.session.add(timeslot)

    # Commit the data to the database.
    db.session.commit()

    # Add tracks.

    # The track name and the email address for each CREM track.
    track_infos = (
      ('Literature', 'literature@penguicon.org'),
      ('Tech', 'tech@penguicon.org'),
      ('After Dark', 'afterdark@penguicon.org'),
      ('Action Adventure', 'action@penguicon.org'),
      ('Costuming', 'costuming@penguicon.org'),
      ('Comics', 'webcomics@penguicon.org'),
      ('Gaming', 'gaming@penguicon.org'),
      ('DIY', 'diy@penguicon.org'),
      ('Food', 'food@penguicon.org'),
      ('Science', 'science@penguicon.org'),
      ('Media', 'media@penguicon.org'),
      ('Mayhem', 'mayhem@penguicon.org'),
      ('Anime', 'anime@penguicon.org'),
      ('Penguicon', 'penguicon@penguicon.org'),
      ('Life', 'life@penguicon.org'),
    )

    # Create tracks and save database objects in dictionary for later reference.
    tracks = {}
    for track_info in track_infos:
        track = Track(track_info[0], track_info[1])
        tracks[track_info[0]] = track
        db.session.add(track)

    # Commit the data to the database.
    db.session.commit()

    # Add room groups.

    room_group_names = (
        'Algonquin',
        'Charlevoix',
        'Lobby',
    )

    for room_group_name in room_group_names:
        room_group = RoomGroup(room_group_name)
        db.session.add(room_group)

    # Commit the data to the database.
    db.session.commit()

    # Add rooms.

    # For each room, the name, square feet, capacity and room group it belongs to.
    room_infos = (
        ('Algonquin A', 1207, 100, 'Algonquin'),
        ('Algonquin B', 1207, 100, 'Algonquin'),
        ('Algonquin C', 1207, 100, 'Algonquin'),
        ('Algonquin D', 1207, 100, 'Algonquin'),
        ('Algonquin Foyer', 3000, 450, None),
        ('Charlevoix A', 756, 64, 'Charlevoix'),
        ('Charlevoix B', 756, 64, 'Charlevoix'),
        ('Charlevoix C', 756, 64, 'Charlevoix'),
        ('Portage Auditorium', 1439, 68, None),
        ('Windover', 1475, 40, None),
        ('TC Linguinis', 1930, 40, None),
        ('Baldwin Board Room', 431, 12, None),
        ('Board of Directors', 511, 15, None),
        ('Board of Governors', 391, 5, None),
        ('Board of Regents', 439, 15, None),
        ('Board of Trustees', 534, 40, None),
        ('Hamlin', 360, 25, None),
        ('Montcalm', 665, 50, None),
        ('Nicolet', 667, 50, None),
        ('Game Table A', 20, 10, 'Lobby'),
        ('Game Table B', 20, 10, 'Lobby'),
        ('Game Table C', 20, 10, 'Lobby'),
        ('Game Table D', 20, 10, 'Lobby'),
    )

    # Create rooms and save database objects in dictionary for later reference.
    rooms = {}
    for room_info in room_infos:
        room = Room()
        room.room_name = room_info[0]
        room.room_sq_ft = room_info[1]
        room.room_capacity = room_info[2]
        if room_info[3]:
            room.room_group = db.session.query(RoomGroup).\
                filter(RoomGroup.room_group_name == room_info[3]).first()
        rooms[room.room_name] = room
        db.session.add(room)

    # Commit the data to the database.
    db.session.commit()

    # Keep track of presenters.
    presenters = {}

    # Read events from file.
    with open(sched_info_fname, 'rb') as csvfile:
        csvreader = csv.reader(csvfile, delimiter=',', quotechar='"')
        first_row = True
        for row in csvreader:
            app.logger.info(row)
            if first_row:
                first_row = False
                continue
            if len(row) < 11:
                load_error = DataLoadError()
                load_error.error_level = 'Error'
                load_error.destination_table = 'event'
                load_error.line_num = csvreader.line_num
                load_error.error_msg = 'Not enough columns in row %d' % csvreader.line_num
                load_error.error_dt = datetime.datetime.now()
                db.session.add(load_error)
                num_errors += 1
                continue

            trackname = row[6].split(',')[0].strip()
            if trackname not in tracks:
                # There is no corresponding track, so add it.
                email = '-'.join(trackname.lower().split()) + '-added@penguicon.org'
                track = Track(trackname, email)
                tracks[trackname] = track
                db.session.add(track)

                load_error = DataLoadError()
                load_error.error_level = 'Warning'
                load_error.destination_table = 'event'
                load_error.line_num = csvreader.line_num
                load_error.error_msg = '%s is not a defined track; adding it' % trackname
                load_error.error_dt = datetime.datetime.now()
                db.session.add(load_error)
                num_errors += 1
                continue
            event = Event()
            event.title = row[0]
            event.description = row[7]
            event.track = tracks[trackname]

            # Add timeslots and duration.
            try:
                timeslots = get_timeslots(row[1], row[2], row[3], row[4],
                                          convention, Timeslot)
                event.timeslots = timeslots
                event.duration = len(timeslots)
            except Exception as e:
                load_error = DataLoadError()
                load_error.error_level = 'Error'
                load_error.destination_table = 'event'
                load_error.line_num = csvreader.line_num
                load_error.error_msg = str(e)
                load_error.error_dt = datetime.datetime.now()
                db.session.add(load_error)
                num_errors += 1
                continue

            event.facilityRequest = row[10]
            event.convention = convention

            # Add room to the event.
            if row[5].strip():
                if row[5] not in rooms:
                    # This is not a predefined room, so add it.
                    load_error = DataLoadError()
                    load_error.error_level = 'Warning'
                    load_error.destination_table = 'event'
                    load_error.line_num = csvreader.line_num
                    load_error.error_msg = '%s is not a pre-defined room; adding this room' % row[5]
                    load_error.error_dt = datetime.datetime.now()
                    num_warnings += 1
                    db.session.add(load_error)

                    room = Room()
                    room.room_name = row[5]
                    room.room_sq_ft = 0
                    room.room_capacity = 0
                    rooms[row[5]] = room
                    db.session.add(room)
                else:
                    room = rooms[row[5]]
                event.rooms.append(room)

            # Add presenters.
            if row[8].strip():
                presenter_names = row[8].split(',')
                presenter_names = [s.strip() for s in presenter_names]
                for presenter_name in presenter_names:
                    if presenter_name in presenters:
                        presenter = presenters[presenter_name]
                    else:
                        last_name = presenter_name.split(' ')[-1].strip()
                        first_name = ' '.join(presenter_name.split(' ')[0:-1]).strip()
                        presenter = Presenter(first_name, last_name)
                        presenters[presenter_name] = presenter
                        db.session.add(presenter)
                    event.presenters.append(presenter)

            db.session.add(event)

    # Commit the data to the database.
    db.session.commit()

    # Return the number of errors and warnings.
    return num_errors, num_warnings

if __name__ == '__main__':
    """
    Allows the data to be loaded from the command line, by passing the
    file name(s) as command line arguments.
    """
    # Get the name of the files with schedule and convention information.
    if len(sys.argv) < 2:
        sys.stderr.write('Error: schedule information file not specified\n')
        sys.exit(1)
    sched_info_fname = sys.argv[1]

    # Make sure the file with schedule information exists.
    if not os.path.exists(sched_info_fname):
        sys.stderr.write('Error: %s does not exist\n' % sched_info_fname)
        sys.exit(1)

    # Get the name of file with convention information if specified.
    if len(sys.argv) > 2:
        convention_info_fname = sys.argv[2]
        if not os.path.exists(convention_info_fname):
            sys.stderr.write('Error: %s does not exist\n' % convention_info_fname)
            sys.exit(1)

    # Replace the data in the database.
    num_errors, num_warnings = refresh_data(sched_info_fname,
                                            convention_info_fname=CONVENTION_INFO_FNAME)
    sys.stderr.write('%d errors; %d warnings\n' % (num_errors, num_warnings))
