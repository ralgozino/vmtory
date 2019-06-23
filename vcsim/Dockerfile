FROM golang

RUN go get -u github.com/vmware/govmomi/vcsim

CMD ["vcsim", "-esx", "-l", "0.0.0.0:8989"]
