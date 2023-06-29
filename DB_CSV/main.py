import pandas as pd
import datetime as dt

PATH_TO_CSV = f'./data/init_data_for_db.csv'
DATE_FORMAT = '%d.%m.%Y'

data = pd.read_csv(PATH_TO_CSV, encoding='utf-16')
init_df = pd.DataFrame(data, columns=['Имя','Телефон','Сайт','Заезд','Выезд','Сумма','Базовая цена','Статус','Дата'])

dates = pd.DataFrame({'check-in_date': init_df['Заезд'].apply(lambda x: dt.datetime.strptime(x, DATE_FORMAT).date()),
                      'check-out_date': init_df['Выезд'].apply(lambda x: dt.datetime.strptime(x, DATE_FORMAT).date())})



def replace_value_by_ind(value, table_id):
    if pd.notnull(value):
        return table_id[table_id.iloc[:, 0] == value].index[0]
    else:
        return value

def table_of_uniques(df, col_name):
    df1 = pd.DataFrame(df[col_name]).dropna().drop_duplicates()
    df1.reset_index(drop=True, inplace=True)
    df1.index += 1
    return df1

def check_dates(day):
    #day = dt.datetime.strptime(day, DATE_FORMAT).date()
    if day < dt.date.today():
        return 0
    else:
        for index, row in dates.iterrows():
            if day >= row['check-in_date'] and day < row['check-out_date']:
                return 0
    return 1

# source table
source = table_of_uniques(init_df, 'Сайт')

# tenant table
tenant = table_of_uniques(init_df, ['Телефон', 'Имя'])

# status table
status = pd.DataFrame({'name': ['Завершен', 'Ожидается', 'Отменен']})
status.index += 1

# booking table
booking = pd.DataFrame({'id_flat': 1,
                        'id_source': init_df['Сайт'].apply(lambda x: replace_value_by_ind(x, source)),
                        'id_status': init_df['Статус'],
                        'check-in_date': dates['check-in_date'],
                        'check-out_date': dates['check-out_date'],
                        'price': init_df['Сумма'],
                        'booking_date': init_df['Дата'].apply(lambda x: dt.datetime.strptime(x, DATE_FORMAT).date()),
                        'comment': None})

booking.index += 1

# booking-tenant table
booking_tenant = pd.DataFrame({'phone': init_df['Телефон']})
booking_tenant.index += 1

# calendar table
start_date = dt.datetime(2022, 4, 17)
end_date = dt.date.today() + dt.timedelta(days = 365)
cal = pd.DataFrame({'Dates': pd.date_range(start_date, end_date).strftime('%d.%m.%Y')})
cal['Dates'] = cal['Dates'].apply(lambda x: dt.datetime.strptime(x, DATE_FORMAT).date())
calendar = pd.DataFrame({'date': cal['Dates'],
                        'id_flat': 1,
                        'base_price': 2500,
                        'min_nights_amount': 2,
                        'is_available': cal['Dates'].apply(lambda x: check_dates(x))})

# flat table
flat = pd.DataFrame({'id_landlord': [1],
                     'name': 'Rest&Calm',
                     'address': 'St.Petersburg, Lenina str, 58, 12',
                     'add_date': '2022-04-17',
                     'link_sites': 'http/smth.ru',
                     'link_tenants': 'http/smth.ru/user',
                     'comment': None})
flat.index += 1

# flat-source table
flat_source = pd.DataFrame({'id_flat': 1,
                'id_source': [1, 2, 3, 4, 5]})

# discount table
discount = pd.DataFrame({'nights_amount': [7, 15, 30],
                         'discount': [5, 7, 10]})
discount.index += 1


# flat-discount table
flat_discount = pd.DataFrame({'id_flat': 1,
                              'id_discount': [1, 2, 3]})
flat_discount.index += 1

# landlord table
landlord = pd.DataFrame({'name': ['Ирина'],
                         'e-mail': 'irina_studia@mail.ru',
                         'password': '12345',
                         'registration_date': '2022-04-17',
                         'edit_date': '2022-04-17'})
landlord.index += 1

if __name__ == '__main__':

    db_tables = {'source': source,
                 'tenant': tenant,
                 'status': status,
                 'booking': booking,
                 'booking_tenant': booking_tenant,
                 'calendar': calendar,
                 'flat': flat,
                 'flat_source': flat_source,
                 'discount': discount,
                 'flat_discount': flat_discount ,
                 'landlord': landlord}

    for name, table in db_tables.items():
        table.fillna('\\N', inplace=True)
        if 'flat_' in name or name == 'calendar' or name == 'tenant':
            ind = False
        else:
            ind = True
        table.to_csv(r'./data/csv_tables/' + name + '.csv', header=False, index=ind)