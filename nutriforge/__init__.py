# Optional: lets Windows users run MySQL with PyMySQL if mysqlclient fails to install.
try:
    import pymysql
    pymysql.install_as_MySQLdb()
except ImportError:
    pass
