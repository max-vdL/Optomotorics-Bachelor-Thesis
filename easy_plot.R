library(dygraphs)
library(ggplot2)
library(reshape2)
library(plotly)

# Lists for saving of data from multiple test flys
even_flylist <- list()
odd_flylist <- list()


global_data <- function() {
  rawdatafile <<- file.choose()
  name <<- basename(rawdatafile)
  
  readdata <<- read.csv(rawdatafile, header = FALSE, sep = " ")
  
  flydata <<- readdata[c(1)]
  
  arenadata <<- readdata[c(2)]
  
  time <- readdata[c(3)]
  
  perioddata <<- readdata[c(4)]
  
  rawdata0 <<- readdata[c(3, 1, 2 ,4)]
  rawdata <<- cbind(time, flydata, arenadata, perioddata)
}


# accumulating of all even/odd datapoints in lists (no time reference) and calculating averages
even_odd_sorting <- function(perioddata, flydata) {
  fly_even <- list()
  fly_odd <- list()
  i <- 1
  a <- 1
  b <- 1
  while (TRUE) {
    if (perioddata[i, c(1)] %% 2 == 0) {
      fly_even[[a]] <- flydata[i, c(1)]
      a = a +1
      i = i +1
    }
    else {
      fly_odd[[b]] <- flydata[i, c(1)]
      b = b +1
      i = i +1
    }
  }
  average_even_period = Reduce("+",fly_even)/length(fly_even)
  average_odd_period = Reduce("+",fly_odd)/length(fly_odd)
  print(average_even_period)
  print(average_odd_period)
  
  general_average = (average_odd_period + average_even_period) / 2
  print(general_average)
  
  average_difference = average_odd_period - average_even_period
  print(average_difference)
}


# removes the voltage jumps in the arena data and gives proper column names
arenadata_smoothing <- function(rawdata) {
  names(rawdata) <- c("time", "fly", "arena", "period")
  arena_min <- min(rawdata[7400:7500, c(3)])
  for (i in 1:nrow(rawdata)) {
    if (rawdata[i, c(3)] > (arena_min + 3.5)) {
      rawdata[i, c(3)] <- rawdata[i-1, c(3)]
    }
  }
  rawdata <<- rawdata
}

# sorting of the rawdata by period into one list: periodlist
period_sorting <- function(rawdata){
  periodcount = 0
  row = 1
  periodlist <- list()
  rawdata_max = nrow(rawdata)
  while (row <= rawdata_max) {
    periodname <- paste("Period", periodcount, sep = "")
    d = 1
    temp <- list()
    while ((rawdata[row, c(4)] == periodcount)) {
      temp[[d]] <- rawdata[row, c(2)]
      d = d +1
      row = row +1
      if (is.na(rawdata[row, c(4)])) {break}
    }
    periodlist[[periodname]] <- temp
    periodcount = periodcount +1
  }
  periodlist <<- periodlist
  
  # figure the length of the smallest list in "periodlist" out to avoid stepping over list boundaries
  templist <- list()
  for (i in 1:length(periodlist)) {
    templist[[i]] <- length(periodlist[[i]])
  }
  max_perioddata <<- min(unlist(templist))
}

# merging of all even Periods into one List: merged_even_periods
data_merging_even_period <- function(rawdata) {
  period_sorting(rawdata)
  i = 1
  x = 1
  a = 1
  merged_even_periods <<- list()
  for (x in 1:max_perioddata) {
    point = 0
    count = 0
    for (i in seq(from=1, to=length(periodlist), by=2)) {
      point = point + periodlist[[i]][[x]]
      count = count +1
    }
    average = point/count
    merged_even_periods[[a]] <<- average
    a = a +1
  }
}

# merging of all odd Periods into one List: merged_odd_periods
data_merging_odd_period <- function(rawdata) {
  period_sorting(rawdata)
  i = 1
  x = 1
  a = 1
  merged_odd_periods <<- list()
  for (x in 1:max_perioddata) {
    point = 0
    count = 0
    for (i in seq(from=2, to=length(periodlist), by=2)) {
      point = point + periodlist[[i]][[x]]
      count = count +1
    }
    average = point/count
    merged_odd_periods[[a]] <<- average
    a = a +1
  }
}

# exercise plotting Function for all even periods combined, write merged data to list
even_merged_plot <- function() {
  data_merging_even_period(rawdata)
  mean <- do.call("rbind", merged_even_periods)
  freq <- c(1:length(merged_even_periods))
  data <- as.data.frame(mean)
  plotdata <- cbind(data, freq)
  print(
    ggplot(plotdata, aes(x=freq, y=V1)) + 
          geom_line(aes(y=V1)) +
          ggtitle("Powerspectra") +
          geom_smooth()
  )
  # save the merged data in the flylist for future mergign of different flys
  even_flylist[[name]] <<- as.list(mean)
}

# exercise plotting Function for all odd periods combined, write merged data to list
odd_merged_plot <- function() {
  data_merging_odd_period(rawdata)
  mean <- do.call("rbind", merged_odd_periods)
  freq <- c(1:length(merged_odd_periods))
  data <- as.data.frame(mean)
  plotdata = cbind(data, freq)
  print(
    ggplot(plotdata, aes(x=freq, y=V1)) + 
      geom_line(aes(y=V1)) +
      ggtitle("Powerspectra") +
      geom_smooth()
  )
  # save the merged data in the flylist for future mergign of different flys
  odd_flylist[[name]] <<- as.list(mean)
}

# plottiong Function for all even periods seperated in one Graph
even_period_plot <- function() {
  arenadata_smoothing(rawdata)
  period_sorting(rawdata)
  n <- as.list(c(1:max_perioddata))
  time <- do.call("rbind", n)
  period0 <- as.list(periodlist[[1]][1:max_perioddata])
  period2 <- as.list(periodlist[[3]][1:max_perioddata])
  period4 <- as.list(periodlist[[5]][1:max_perioddata])
  period6 <- as.list(periodlist[[7]][1:max_perioddata])
  period8 <- as.list(periodlist[[9]][1:max_perioddata])
  plotdata <- as.data.frame(time)
  plotdata["period0"] <- unlist(period0)
  plotdata["period2"] <- unlist(period2)
  plotdata["period4"] <- unlist(period4)
  plotdata["period6"] <- unlist(period6)
  plotdata["period8"] <- unlist(period8)
  plotdata_new <- melt(plotdata, id = c("V1"))
  names(plotdata_new) <- c("time", "period", "fly")
  print(
    ggplot(plotdata_new, aes(x=time, y=fly)) + 
      geom_line(aes(color = period)) +
      geom_smooth() +
      ggtitle("Even period plot") #+
      #geom_smooth()
  )
}


# plottiong Function for all odd periods seperated in one Graph
odd_period_plot <- function() {
  arenadata_smoothing(rawdata)
  period_sorting(rawdata)
  n <- as.list(c(1:max_perioddata))
  time <- do.call("rbind", n)
  period0 <- as.list(periodlist[[2]][1:max_perioddata])
  period2 <- as.list(periodlist[[4]][1:max_perioddata])
  period4 <- as.list(periodlist[[6]][1:max_perioddata])
  period6 <- as.list(periodlist[[8]][1:max_perioddata])
  period8 <- as.list(periodlist[[10]][1:max_perioddata])
  plotdata <- as.data.frame(time)
  plotdata["period1"] <- unlist(period0)
  plotdata["period3"] <- unlist(period2)
  plotdata["period5"] <- unlist(period4)
  plotdata["period7"] <- unlist(period6)
  plotdata["period9"] <- unlist(period8)
  plotdata_new <- melt(plotdata, id = c("V1"))
  names(plotdata_new) <- c("time", "period", "fly")
  print(
    ggplot(plotdata_new, aes(x=time, y=fly)) + 
      geom_line(aes(color = period)) +
      geom_smooth() +
      ggtitle("Odd period plot") #+
    #geom_smooth()
  )
}


# even_period_plot2 <- function(rawdata) {
#   rawdata <- arenadata_smoothing(rawdata)
#   print(
#     ggplot(rawdata, aes(x=time, y=fly, colour=period)) + 
#       geom_point() +
#       ggtitle("Powerspectra") #+
#     #geom_smooth()
#   )
# }


# simple plotting function with dygraphs for the whole rawdata
single_fly_plot <- function() {
  arenadata_smoothing(rawdata)
  dygraph(rawdata, main = "test graph") %>%
    dyRangeSelector() %>%
    dyRoller(showRoller = TRUE, rollPeriod = 0) %>%
    dySeries("fly", label = "Fly", color = "darkred") %>%
    dySeries("arena", label = "Arena") %>%
    dySeries("period", label = "Period") %>%
    dyAxis("y", label = "Voltage (V)") %>%
    dyAxis("x", label = "Time (millisec.)")
}




################ FINAL EVALUATION OF ALL FLYS ####################

# merging of the merged even periods from all test flys into one List: merged_even_flys
data_merging_even_flys <- function(rawdata) {
  i = 1
  x = 1
  a = 1
  merged_even_flys <<- list()
  
  # figure the length of the smallest list in "even_flylist" out to avoid stepping over list boundaries
  templist <- list()
  for (i in 1:length(even_flylist)) {
    templist[[i]] <- length(even_flylist[[i]])
  }
  max_even_flydata <<- min(unlist(templist))
  
  for (x in 1:max_even_flydata) {
    point = 0
    count = 0
    for (i in seq(from=1, to=length(even_flylist), by=2)) {
      point = point + even_flylist[[i]][[x]]
      count = count +1
    }
    average = point/count
    merged_even_flys[[a]] <<- average
    a = a +1
  }
}

# merging of the merged odd periods from all test flys into one List: merged_odd_flys
data_merging_odd_flys <- function(rawdata) {
  i = 1
  x = 1
  a = 1
  merged_odd_flys <<- list()
  
  # figure the length of the smallest list in "odd_flylist" out to avoid stepping over list boundaries
  templist <- list()
  for (i in 1:length(odd_flylist)) {
    templist[[i]] <- length(odd_flylist[[i]])
  }
  max_odd_flydata <<- min(unlist(templist))
  
  for (x in 1:max_odd_flydata) {
    point = 0
    count = 0
    for (i in seq(from=1, to=length(odd_flylist), by=2)) {
      point = point + odd_flylist[[i]][[x]]
      count = count +1
    }
    average = point/count
    merged_odd_flys[[a]] <<- average
    a = a +1
  }
}

# exercise plotting Function for the even periods of all flys combined
even_merged_plot_all_flys <- function() {
  data_merging_even_flys(rawdata)
  mean <- do.call("rbind", merged_even_flys)
  freq <- c(1:length(merged_even_flys))
  data <- as.data.frame(mean)
  plotdata <- cbind(data, freq)
  names(plotdata) <- c("voltage", "time")
  print(
    ggplot(plotdata, aes(x=time, y=voltage)) + 
      geom_line(aes(y=voltage)) +
      geom_smooth() +
      ggtitle("Average all even flys")
  )
}

# exercise plotting Function for the odd periods of all flys combined
odd_merged_plot_all_flys <- function() {
  data_merging_odd_flys(rawdata)
  mean <- do.call("rbind", merged_odd_flys)
  freq <- c(1:length(merged_odd_flys))
  data <- as.data.frame(mean)
  plotdata <- cbind(data, freq)
  names(plotdata) <- c("voltage", "time")
  print(
    ggplot(plotdata, aes(x=time, y=voltage)) + 
      geom_line(aes(y=voltage)) +
      geom_smooth() +
      ggtitle("Average all odd flys")
  )
}


x = unlist(odd_flylistasone, use.names = FALSE)
hist(x, breaks = "Scott")
qplot(x, binwdth = 5)
p = plot_ly(x, type = "histogram")

odd_flylistasone <- c(odd_flylist[[1]], odd_flylist[[2]], odd_flylist[[3]], odd_flylist[[4]], odd_flylist[[5]], odd_flylist[[6]], odd_flylist[[7]], odd_flylist[[8]], odd_flylist[[9]], odd_flylist[[10]], odd_flylist[[11]])
x = unlist(odd_flylistasone, use.names = FALSE)
hist(x, breaks = "Scott", xlim = range(3, 4.5), main = "Histogram of merged odd periods from 11 flys")

odd_singleflyasone <- c(periodlist[[1]], periodlist[[3]], periodlist[[5]], periodlist[[7]], periodlist[[9]])
x = unlist(odd_singleflyasone, use.names = FALSE)
hist(x, breaks = "Scott", xlim = range(3, 4.5), main = "Histogram of all odd periods from fly E11")

even_flylistasone <- c(even_flylist[[1]], even_flylist[[2]], even_flylist[[3]], even_flylist[[4]], even_flylist[[5]], even_flylist[[6]], even_flylist[[7]], even_flylist[[8]], even_flylist[[9]], even_flylist[[10]], even_flylist[[11]])
x = unlist(even_flylistasone, use.names = FALSE)
hist(x, breaks = "Scott", xlim = range(3, 4.5), main = "Histogram of merged even periods from 3 flys")

even_singleflyasone <- c(periodlist[[2]], periodlist[[4]], periodlist[[6]], periodlist[[8]], periodlist[[10]])
x = unlist(even_singleflyasone, use.names = FALSE)
hist(x, breaks = "Scott", xlim = range(3, 4.5), main = "Histogram of all even periods from fly E11")
