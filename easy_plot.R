library(dygraphs)

rawdata <- read.csv("KHZtext.txt", header = FALSE, sep = " ")
flydata <- rawdata[c(3, 1)]
#dygraph(flydata) %>% dyRangeSelector()

arenadata <- rawdata[c(3, 2)]

rawdata <- rawdata[c(3, 1, 2)]

dygraph(rawdata, main = "test graph") %>% 
  dyRangeSelector() 
  # dySeries("V1", name = "fly") %>%
  # dySeries("V2", name = "arena") %>%
  # dyAxis("y", label = "Voltage (V)") %>%
  # 