from util.Database import engine_mssql_ir
from util.SendEmail import send_email
import pandas as pd
import os
import shutil
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.schedulers.background import BackgroundScheduler


DEFAULT_ENCODING = 'utf-8-sig'
os.environ['NLS_LANG'] = ".AL32UTF8"
engine_mssql_ir = engine_mssql_ir()
# sourceFile = "D:\\Test\\F43121.csv"
# targetPath = "D:\\Test\\backup\\"
sourceFile = "\\\\eInvoice\\Outbound\\F43121.csv"
targetPath = "\\\\eInvoice\\Outbound_Archive\\"


def delete_old(dframe, engine):
    try:
        for idx, row in dframe.iterrows():
            str_sql = "delete from [JDEHK_INV_HEADER] where [CompanyNo]= '{}' and " \
                  "[ContractorNo]='{}' and [InvoiceNo]='{}'".format(row['KCOO'], row['SupplierNumber'], row['VR04'])
            engine.execute(str_sql)

            str_sql = "delete from [JDEHK_INV_RECEIVED] where [CompanyNo]= '{}' and " \
                      "[ContractorNo]='{}' and [InvoiceNo]='{}'".format(row['KCOO'], row['SupplierNumber'], row['VR04'])
            engine.execute(str_sql)
    except Exception as e:
        print(e)
        send_email(e, "eInvoice Outbound Delete")


def insert_new(dframe, engine):
    try:
        previousKCOO = ""
        previousVR04 = ""
        previousSupplier = ""
        for idx, row in dframe.iterrows():
            if (row['KCOO'] != previousKCOO) or (row['VR04'] != previousVR04) or (row['SupplierNumber'] != previousSupplier):

                #Special handle for the following company, the "-" is not standard input in JDE, need to replace here.
                if row['KCOO']==22004:
                    CoName="MID-LEVELS PORTFOLIO (AIGBURTH) LIMITED"
                elif row['KCOO']==22006:
                    CoName="MID-LEVELS PORTFOLIO (BRANKSOME) LIMITED"
                elif row['KCOO']==22008:
                    CoName="MID-LEVELS PORTFOLIO (GLADDON) LIMITED"
                elif row['KCOO']==22010:
                    CoName="MID-LEVELS PORTFOLIO (TAVISTOCK) LIMITED"
                elif row['KCOO']==22014:
                    CoName="MID-LEVELS PORTFOLIO (TT1&2) HLDG LIMITED"
                elif row['KCOO']==22015:
                    CoName="MID-LEVELS PORTFOLIO (TREGUNTER TOWERS 1 & 2) LIMITED"
                else:
                    CoName = row['CompanyName']


                if row['ConAssessmentHeader'].rstrip(' ')=="":
                    AssessHeader="N/A"
                elif row['ConAssessmentDetail'].rstrip(' ')=='':
                    AssessHeader="N/A"
                else:
                    AssessHeader=row['ConAssessmentHeader']

                
                    
                str_sql = "INSERT INTO [JDEHK_INV_HEADER] (InvoiceNo,InvoiceDate,WFStatus,VariationOrder,UserID,CompanyNo,PONumber," \
                          "POType,PayItem,ContractorNo,ContractTotal,CompanyName,INFA_ExportFlag,INFA_ImportFlag,INFA_ImportTime,ContractorAssessment)" \
                          "VALUES ('{}',CONVERT(varchar(10), CONVERT(date,'{}', 103), 120),'{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','0','1'," \
                          "CURRENT_TIMESTAMP,'{}')".format(row['VR04'], row['VR05'], row['URCD'], '0', row['UserID'], row['KCOO'], row['DOCO'],
                                                      row['DCTO'], row['SFXO'], row['SupplierNumber'], row['TotalAmount'], CoName, AssessHeader)


                engine.execute(str_sql)

            str_sql = "INSERT INTO [JDEHK_INV_RECEIVED] (CompanyNo,PONumber,POType,PayItem,LineNum,NoOfLine,InvoiceNo,JDENumber," \
                      "TransactionDate,ReceivedDate,VendorInv,PayStatus,GLClass,CostCenter,DocumentType,GLDate,QtyOrdered," \
                      "QtyPaidToDate,QtyOpen,QtyReceived,UnitCost,AmountPaidToDate,AmountOpen,AmountReceived,Currency," \
                      "ItemUnit,ContractorNo,ContractSubject,ContractorName,Combined,ContractorAssessment) " \
                      "VALUES ('{}','{}','{}','{}',CAST({} as int),'{}','{}','{}',CONVERT(varchar(10), CONVERT(date,'{}', 103), 120), CONVERT(varchar(10), CONVERT(date,'{}', 103), 120),'{}','{}','{}','{}','{}'," \
                      "CONVERT(varchar(10), CONVERT(date,'{}', 103), 120),'{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}'" \
                      ")".format(row['KCOO'], row['DOCO'], row['DCTO'], row['SFXO'], row['LNID'], row['NLIN'], row['VR04'], row['DOC'],
                                 row['TRDJ'], row['RCDJ'], row['VINV'], row['PST'], row['GLC'], row['MCU'], row['DCT'], row['DGL'], row['UORG'],
                                 row['UPTD'], row['UOPN'], row['UREC'], row['PRRC'], row['APTD'], row['AOPN'], row['AREC'], row['CRCD'],
                                 row['UOM2'], row['SupplierNumber'], row['ContractorName'].replace("'",""), row['SupplierName'].replace("'",""), str(row['LDTA']).replace("'",""), row['ConAssessmentDetail'])
            
            engine.execute(str_sql)

            previousKCOO = row['KCOO']
            previousVR04 = row['VR04']
            previousSupplier = row['SupplierNumber']

    except Exception as e:
        print(e)
        send_email(e, "eInvoice Outbound Insert")


def job():
    try:
        
        if os.path.exists(sourceFile):
            print("{} : eInvoice outbound scheduler run every 5 minutes".format(datetime.now().strftime("%H:%M:%S")))
            message = "Can\'t backup outbound file"
            # backup file
            now = datetime.now()
            date_time = now.strftime("%Y%m%d%H%M%S")
            target = "{}F43121{}.csv".format(targetPath, date_time)
            shutil.move(sourceFile, target)

            message = "Can\'t fetch csv file"
            # Fetch data from csv
            df2 = pd.read_csv(target,
                              names=['KCOO','DOCO','DCTO','SFXO','LNID','NLIN','DOC','TRDJ','RCDJ','VINV','PST','GLC',
                                     'MCU','DCT','DGL','UORG','UPTD','UOPN','UREC','PRRC','APTD','AOPN','AREC','CRCD',
                                     'UOM2','VR04','VR05','URCD','URAT','LDTA','ContractorName','SupplierNumber',
                                     'SupplierName','UserID','CompanyName','TotalAmount','ConAssessmentHeader','ConAssessmentDetail'],
                              header=None, dtype={'VR04': object, 'SupplierNumber': object})

            # copy distinct record to new dataframe
            df_drop = df2[['KCOO','SupplierNumber','VR04']].drop_duplicates()

            message = "Can\'t delete database records"
            # Delete old record from database
            delete_old(df_drop, engine_mssql_ir)

            message = "Can\'t insert records to database. " + target
            # Insert new record
            insert_new(df2, engine_mssql_ir)
        else:
            print("{} No outbound file exist".format(datetime.now().strftime("%H:%M:%S")))
    except:
        send_email(message, "eInvoice Outbound")


if __name__ == '__main__':
    schedule = BlockingScheduler()
    # schedule = BackgroundScheduler()
    schedule.add_job(job,'interval', minutes=5)

    try:
        schedule.start()

    except Exception as e:
        print(e)
