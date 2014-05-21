# coding=UTF-8

from ckan.lib.base import _

government_depts_raw = """
Attorney General's Office
Cabinet Office
Central Office of Information
Charity Commission for England and Wales
Commissioners for the Reduction of the National Debt
Crown Estate
Crown Prosecution Service
Department for Business, Innovation and Skills
Department for Communities and Local Government
Department for Culture, Media and Sport
Department for Education
Department for Environment, Food and Rural Affairs
Department for International Development
Department for Transport
Department for Work and Pensions
Department of Energy and Climate Change
Department of Health
Export Credits Guarantee Department
Food Standards Agency
Foreign and Commonwealth Office
Forestry Commission
Government Actuary's Department
Government Equalities Office
Her Majesty's Revenue and Customs
Her Majesty's Treasury
Home Office
Ministry of Defence
Ministry of Justice
National School of Government
Northern Ireland Office
Office for Standards in Education, Children's Services and Skills
Office of Fair Trading
Office of Gas and Electricity Markets
Office of Rail Regulation
Office of the Advocate General for Scotland
Office of the Leader of the House of Commons
Office of the Leader of the House of Lords
Office of the Parliamentary Counsel
Postal Services Commission
Public Works Loan Board
Revenue and Customs Prosecutions Office
Scotland Office
Serious Fraud Office
Treasury Solicitor's Department
UK Statistics Authority
UK Trade & Investment
Wales Office
Water Services Regulation Authority

Scottish Government
Welsh Assembly Government
Northern Ireland Executive

Ordnance Survey
Lichfield District Council
Society of Information Technology Management
Warwickshire County Council
"""
government_depts = []
for line in government_depts_raw.split('\n'):
    if line:
        government_depts.append(unicode(line.strip()))

extra_fields = [
                u'title_se',
                u'title_en',
                u'notes_se',
                u'notes_en',
                u'taxonomy_url',
                u'agency',
                u'source',
                u'search_info',
                u'external_reference',
                u'external_reference_se',
                u'external_reference_en',
                u'date_released',
                u'date_updated',
                u'update_frequency',
                u'geographic_granularity',
                u'geographic_coverage',
                u'temporal_granularity',
                u'categories',
                u'temporal_coverage-from',
                u'temporal_coverage-to'
                ]

fields_translated = {
                u'title_se': _('title_se'),
                u'title_en': _('title_en'),
                u'notes_se': _('notes_se'),
                u'notes_en': _('notes_en'),
                u'agency': _('agency'),
                u'source': _('source'),         
                u'search_info': _('search_info'),
                u'taxonomy_url': _('taxonomy_url'),
                u'external_reference': _('external_reference'),
                u'external_reference_se': _('external_reference_se'),
                u'external_reference_en': _('external_reference_en'),
                u'date_released': _('date_released'),
                u'date_updated': _('date_updated'),
                u'update_frequency': _('update_frequency'),
                u'geographic_granularity': _('geographic_granularity'),
                u'geographic_coverage': _('geographic_coverage'),
                u'temporal_granularity': _('temporal_granularity'),
                u'categories': _('categories'),
                u'temporal_coverage-from': _('temporal_coverage-from'),
                u'temporal_coverage-to': _('temporal_coverage-to')
                }

category_options = [
        u'Alue', 
        u'Asuminen', 
        u'Demokratia ja osallistuminen', 
        u'Elinkeinot', 
        u'Elinolot',
        u'Energia- ja vesihuolto',
        u'Julkiset palvelut',
        u'Kartat',
        u'Kaupunkihistoria',
        u'Kiinteistöt',
        u'Koulutus',
        u'Kulttuuri',
        u'Kunnallistalous',
        u'Liikenne',
        u'Maankäyttö',
        u'Muut palvelut',
        u'Oikeuslaitos ja turvallisuus',
        u'Rakennukset',
        u'Rakentaminen',
        u'Sosiaalitoimi',
        u'Talous',
        u'Terveys',
        u'Tulot ja kulutus',
        u'Työmarkkinat',
        u'Vapaa-aika',
        u'Väestö ja väestönmuutokset',
        u'Ympäristö',
        u'Yritykset']

state_options = [u'Helsingin seutu (kaikki)', u'Helsinki', u'Espoo', u'Vantaa', u'Kauniainen', u'Hyvinkää', u'Järvenpää', u'Kerava', u'Kirkkonummi', u'Nurmijärvi', u'Mäntsälä', u'Sipoo', u'Pornainen', u'Tuusula', u'Vihti']

geographic_granularity_options = [u'Valtio', u'Seutu', u'Kunta', u'Tilastoalue', u'Ruutu', u'Piste']

temporal_granularity_options = [u'vuosi', u'vuosineljännes', u'kuukausi']
