library(dygraphs)
library(ggplot2)
library(reshape2)
library(plotly)

# Lists for saving of data from multiple test flys
evenPeriods_allFlys <- list()
oddPeriods_allFlys <- list()


global_data <- function() {
  rawdatafile <<- file.choose()
  name <<- basename(rawdatafile)
  
  readdata <<- read.csv(rawdatafile, header = FALSE, sep = " ")
  
  flydata <<- readdata[c(1)]
  
  arenadata <- readdata[c(2)]
  
  time <- readdata[c(3)]
  
  perioddata <<- readdata[c(4)]
  
  rawdata <<- cbind(time, flydata, arenadata, perioddata)
  
  arenadata_smoothing(rawdata)
}


# accumulating of all even/odd datapoints in lists (no time reference) 
# and calculating averages
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
} # unused at the moment


# removes the voltage jumps in the arena data and gives proper column names
arenadata_smoothing <- function(rawdata) {
  names(rawdata) <- c("time", "fly", "arena", "period")
  arena_min <- min(rawdata[1:(nrow(rawdata)/2), c(3)])
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
  periodlist_ <- list()
  max_row = nrow(rawdata)
  while (row <= max_row) {
    periodname <- paste("Period", periodcount, sep = "")
    i = 1
    temp <- list()
    while ((rawdata[row, c(4)] == periodcount)) {
      temp[[i]] <- rawdata[row, c(2)]
      i = i +1
      row = row +1
      if (is.na(rawdata[row, c(4)])) {break}
      # break if subscript is out of bounds
    }
    periodlist_[[periodname]] <- temp
    periodcount = periodcount +1
  }
  periodlist <<- periodlist_
  
  # figure the length of the smallest list in "periodlist" out
  # to avoid stepping over list boundaries
  temp2 <- list()
  for (i in 1:length(periodlist)) {
    temp2[[i]] <- length(periodlist[[i]])
  }
  max_perioddata <<- min(unlist(temp2))
}

######## data merging

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

######## plotting of merged data

# exercise plotting Function for all even periods combined,
# write merged data to list
even_merged_plot <- function() {
  data_merging_even_period(rawdata)
  mean <- do.call("rbind", merged_even_periods)
  freq <- c(1:length(merged_even_periods))
  data <- as.data.frame(mean)
  names(data) <- c("FlyPosition")
  plotdata <- cbind(data, freq)
  plotname <- paste("Plot of merged even periods from", name)
  print(
    ggplot(plotdata, aes(x=freq, y=FlyPosition)) + 
          geom_line(aes(y=FlyPosition)) +
          ggtitle(plotname) +
          geom_smooth()
  )
  # save the merged data in the flylist for future mergign of different flys
  evenPeriods_allFlys[[name]] <<- as.list(mean)
}

# exercise plotting Function for all odd periods combined,
# write merged data to list
odd_merged_plot <- function() {
  data_merging_odd_period(rawdata)
  mean <- do.call("rbind", merged_odd_periods)
  freq <- c(1:length(merged_odd_periods))
  data <- as.data.frame(mean)
  names(data) <- c("FlyPosition")
  plotdata = cbind(data, freq)
  plotname <- paste("Plot of merged odd periods from", name)
  print(
    ggplot(plotdata, aes(x=freq, y=FlyPosition)) + 
      geom_line(aes(y=FlyPosition)) +
      ggtitle(plotname) +
      geom_smooth()
  )
  # save the merged data in the flylist for future mergign of different flys
  oddPeriods_allFlys[[name]] <<- as.list(mean)
}

######## plotting of individual periods

# plottiong Function for all even periods seperated in one Graph
even_period_plot <- function() {
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
  plotname <- paste("Even period plot", name)
  print(
    ggplot(plotdata_new, aes(x=time, y=fly)) + 
      geom_line(aes(color = period)) +
      geom_smooth() +
      ggtitle(plotname)
  )
}

# plottiong Function for all odd periods seperated in one Graph
odd_period_plot <- function() {
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
  plotname <- paste("Odd period plot", name)
  print(
    ggplot(plotdata_new, aes(x=time, y=fly)) + 
      geom_line(aes(color = period)) +
      geom_smooth() +
      ggtitle(plotname)
  )
}

######## histogram plotting

# histogram plotting functions for the frequency of 
# flydatapoints in even/odd periods
histogram_even <- function() {
  period_sorting(rawdata)
  even_singleflyasone <- c(
    periodlist[[2]], periodlist[[4]], periodlist[[6]],
    periodlist[[8]], periodlist[[10]])
  x = unlist(even_singleflyasone, use.names = FALSE)
  histname <- paste("Histogram of all even periods from fly ", name)
  hist(
    x, breaks = "Scott", xlim = range(0, 3), ylim = range(0, 3200),
    main = histname)
}

histogram_odd <- function() {
  period_sorting(rawdata)
  odd_singleflyasone <- c(
    periodlist[[1]], periodlist[[3]], periodlist[[5]],
    periodlist[[7]], periodlist[[9]])
  x = unlist(odd_singleflyasone, use.names = FALSE)
  histname <- paste("Histogram of all odd periods from fly ", name)
  hist(
    x, breaks = "Scott", xlim = range(0, 3), ylim = range(0, 3200), 
    main = histname)
}


######## flytrace plotting

# simple plotting function with dygraphs for the whole rawdata
single_fly_plot <- function() {
  graphname <- paste("Flytraces from", name)
  dygraph(rawdata, main = graphname) %>%
    dyRangeSelector() %>%
    dyRoller(showRoller = TRUE, rollPeriod = 0) %>%
    dySeries("fly", label = "Fly", color = "darkred") %>%
    dySeries("arena", label = "Arena") %>%
    dySeries("period", label = "Period") %>%
    dyAxis("y", label = "Voltage (V)") %>%
    dyAxis("x", label = "Time (millisec.)")
}




################ FINAL EVALUATION OF ALL FLYS ####################

# merging of the merged even periods from all test flys into one List:
# merged_even_flys
data_merging_even_flys <- function(rawdata) {
  i = 1
  x = 1
  a = 1
  merged_even_flys <<- list()
  
  # figure the length of the smallest list in "even_flylist" out 
  # to avoid stepping over list boundaries
  templist <- list()
  for (i in 1:length(evenPeriods_allFlys)) {
    templist[[i]] <- length(evenPeriods_allFlys[[i]])
  }
  max_even_flydata <<- min(unlist(templist))
  
  for (x in 1:max_even_flydata) {
    point = 0
    count = 0
    for (i in seq(from=1, to=length(evenPeriods_allFlys), by=2)) {
      point = point + evenPeriods_allFlys[[i]][[x]]
      count = count +1
    }
    average = point/count
    merged_even_flys[[a]] <<- average
    a = a +1
  }
}

# merging of the merged odd periods from all test flys into one List: 
# merged_odd_flys
data_merging_odd_flys <- function(rawdata) {
  i = 1
  x = 1
  a = 1
  merged_odd_flys <<- list()
  
  # figure the length of the smallest list in "odd_flylist" out 
  # to avoid stepping over list boundaries
  templist <- list()
  for (i in 1:length(oddPeriods_allFlys)) {
    templist[[i]] <- length(oddPeriods_allFlys[[i]])
  }
  max_odd_flydata <<- min(unlist(templist))
  
  for (x in 1:max_odd_flydata) {
    point = 0
    count = 0
    for (i in seq(from=1, to=length(oddPeriods_allFlys), by=2)) {
      point = point + oddPeriods_allFlys[[i]][[x]]
      count = count +1
    }
    average = point/count
    merged_odd_flys[[a]] <<- average
    a = a +1
  }
}

######## plotting of merged data from all flys

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
      ggtitle("Average all even flys (no arenaturn)")
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
      ggtitle("Average all odd flys (no arenaturn)")
  )
}

######## histogram plotting of merged data from all flys

# histogram plotting function for alls fly data combined 
# (even/odd_flylist required)
histogram_odd_all <- function() {
  odd_flylistasone <- c(oddPeriods_allFlys[[1]], oddPeriods_allFlys[[2]], oddPeriods_allFlys[[3]])
  x = unlist(odd_flylistasone, use.names = FALSE)
  hist(
    x, breaks = "Scott", xlim = range(0, 3),
    main = "Histogram of merged odd periods from D1, D2, D4 flys (no arenaturn)")
}

histogram_even_all <- function() {
  even_flylistasone <- c(evenPeriods_allFlys[[1]], evenPeriods_allFlys[[2]], evenPeriods_allFlys[[3]])
  x = unlist(even_flylistasone, use.names = FALSE)
  hist(
    x, breaks = "Scott", xlim = range(0, 3),
    main = "Histogram of merged even periods from D1, D2, D4 flys (no arenaturn)")
}

