bind = "127.0.0.1:8000"
workers = 1
worker_class = "sync"

timeout = 30
graceful_timeout = 30
keepalive = 5

accesslog = "-"
errorlog = "-"
capture_output = True
access_log_format = '%(h)s "%(m)s %(U)s" %(s)s %(B)s %(L)s'

control_socket_disable = True
