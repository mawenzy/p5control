'<ADbasic Header, Headerversion 001.001>
' Process_Number                 = 10
' Initial_Processdelay           = 2833
' Eventsource                    = Timer
' Control_long_Delays_for_Stop   = No
' Priority                       = High
' Version                        = 3
' ADbasic_Version                = 6.3.1
' Optimize                       = Yes
' Optimize_Level                 = 1
' Stacksize                      = 1000
' Info_Last_Save                 = DESKTOP-T9V68NA  DESKTOP-T9V68NA\BlueFors
'<Header End>
'
' Important!!! compile as process nr. 10!
'

#Include ADwinGoldII.inc

#Define Buffersize 4000000 ' FIFO length
#define takt 0.00000001 ' 10^-8ns, 100kHz
#DEFINE pi2 6.28318531 ' 2 * 3.14159265
#DEFINE zwei15 32768 ' 2^15
#DEFINE zwei16 65536 ' 2^16
#DEFINE zwei24 16777216 ' 2^24
#DEFINE zwei23 8388608 ' 2^23
#DEFINE zwei31 2147483648 ' 2^31
#DEFINE zwei32 4294967296 ' 2^32
#DEFINE range 20 ' output voltage range

Dim Data_1[Buffersize] as Float as FIFO ' V1
Dim Data_2[Buffersize] as Float as FIFO ' V2
Dim Data_3[Buffersize] as Float as FIFO ' X1
Dim Data_4[Buffersize] as Float as FIFO ' X2
Dim Data_5[Buffersize] as Float as FIFO ' Y1
Dim Data_6[Buffersize] as Float as FIFO ' Y2
Dim Data_8[Buffersize] as Long as FIFO ' trigger
Dim Data_9[Buffersize] as Float as FIFO ' time
  
Dim count, now, before as Long
Dim tic, toc as Long
Dim time, delta_t as Float

Dim t1, period as Long
Dim sweep_amplitude, sweep_frequency as Float
Dim lockin_amplitude, lockin_frequency as Float
Dim sweep_value, sin_value, cos_value, value as Float

Dim state, last_state, trigger as Long

Dim ch1, mean1, X1, Y1 as Float
Dim ch2, mean2, X2, Y2 as Float

Init:
  ' Clear FIFOs
  FIFO_Clear(1)
  FIFO_Clear(2)
  FIFO_Clear(3)
  FIFO_Clear(4)
  FIFO_Clear(5)
  FIFO_Clear(6)
  FIFO_Clear(8)
  FIFO_Clear(9)
  
  ' Min ProcessDelay that is Prime
  ProcessDelay = 1987 ' 10ns
  ' 19870ns delay => 150.981kHz, 6.62333us
  
  ' Range Pattern
  Par_1 = 00b
  Par_2 = 00b
    
  ' Voltage Ranges
  FPar_1 = 20
  FPar_2 = 20
  
  ' Start Measuring / Clear FIFO
  Par_8  = 0
  
  ' Averaging Factor  
  Par_9  = 10
  
  ' Lockin (f, A)
  FPar_11 = 10 ' Hz
  FPar_12 = 0.1 ' V
  
  ' Sweep (f, A)
  FPar_13 = 1 ' Hz
  FPar_14 = 1 ' V
  
  ' if Sweeping
  Par_10 = 0
  
  ' Initialize Variables
  ch1 = 0.0 : mean1 = 0.0 : X1 = 0.0 : Y1 = 0.0
  ch2 = 0.0 : mean2 = 0.0 : X2 = 0.0 : Y2 = 0.0
  count = 0 : time = 0 : now = 0 : t1 = 0
  state = 0 : last_state = 0 : trigger = 0
  
  before = Digin_Fifo_Read_Timer() + zwei31
  period = .5 / FPar_13 / takt
  value = zwei16 / range * (FPar_14 + FPar_12) + zwei15
  
  ' Initialize Output
  Write_DAC(1,value) ' Set output DAC1
  Write_DAC(2,zwei16 - value) ' Set output DAC2
  Start_DAC() ' Output On
  
EVENT:   
  ' Convert Analog to Digital
  ' Gold-HW II p.78
  ' Value = ( SUM / N - ( bits / 2 ) ) / bits * Range
  ' p.15 ADwin Gold II Handbook
  
  ' Set Multiplexer on channel with amplifier pattern
  Set_Mux1((000b | shift_left(Par_1, 3))) ' (1st ch row 1)
  Set_Mux2((000b | shift_left(Par_2, 3))) ' (1st ch row 2)
  
  IO_SLEEP(200) ' Waits for 2us until MUX is settled
  Start_Conv(11b) ' Starts Conversion
  
''''' start use of waiting time '''''

  ' Calculate Time
  ' get timestamp between 1 and 2^32
  now = Digin_Fifo_Read_Timer() + zwei31
  delta_t = now - before 
  ' avoid phase slips
  If (delta_t <= 0) Then
    delta_t = now-before + zwei32
  endif
  time = time + delta_t * takt
  before = now
  
  ' Convert Digital to Analog
  
  ' Lock-in, lockin_value [-1, 1]
  sin_value = sin(pi2 * FPar_11 * time)
  cos_value = cos(pi2 * FPar_11 * time)
  
  
  ' Sweep
  ' - sweep_value [-1, 1]
  ' - trigger {-1, 0, N} / {cv, no output, sweep count}
  
  ' sweep
  if (Par_10 = 1) Then
    t1 = t1 + delta_t  
    if (t1 <= period) Then
      sweep_value = 1 - 2 * (t1 / period)
      state = 1
    endif
    if (t1 > period) Then
      if (t1 <= 2 * period) Then
        sweep_value = -1 + 2 * (t1 / period - 1)
        state = 2
      endif
      if (t1 > 2 * period) Then
        t1 = t1 - 2 * period
        sweep_value = 1 - 2 * (t1 / period)
        state = 1      
      endif
    endif
    
    ' Check if no output
    if (FPar_14 = 0.0) Then
      trigger = 0 : state = 0
    endif
  endif
  
  ' cv
  if (Par_10 = 0) Then
    t1 = 0 : sweep_value = 1
    trigger = -1 : state = 0
    
    ' Check if no output
    ' - trigger = 0
    if (FPar_14 = 0.0) Then
      trigger = 0
    endif
    
    
  endif
  
  ' Increment trigger counter
  if (state<>last_state) Then
    if (trigger = -1) Then Inc(trigger)
    Inc(trigger)
    last_state = state
  endif
  
    
    
  ' Calculate and Set Output Value
  value = zwei16 / range * (FPar_14 * sweep_value + FPar_12 * sin_value) + zwei15
  
  Write_DAC(1, value) ' Set output DAC1
  Write_DAC(2, zwei16 - value) ' Set output DAC2
  Start_DAC() ' Update Output
  
''''' end use of waiting time '''''
  
  Wait_EOC(11b) ' Wait for Conversion
  
  ch1 = (Read_ADC24(1) - zwei23) / zwei24 * FPar_1 ' ch1
  ch2 = (Read_ADC24(2) - zwei23) / zwei24 * FPar_2 ' ch2
  
  mean1 = mean1 + ch1
  mean2 = mean2 + ch2
  
  X1 = X1 + ch1 * sin_value
  X2 = X2 + ch2 * sin_value
  
  Y1 = Y1 + ch1 * cos_value
  Y2 = Y2 + ch2 * cos_value
  
  ' Calculation of Averaging
  If (count >= Par_9) Then
    period = .5 / FPar_13 / takt
    
    If (Par_8 = 1) Then
      FIFO_Clear(1)
      FIFO_Clear(2)
      FIFO_Clear(3)
      FIFO_Clear(4)
      FIFO_Clear(5)
      FIFO_Clear(6)
      FIFO_Clear(8)
      FIFO_Clear(9)
      time = 0
      t1 = 0
      Par_8 = 0
    endif
      
    ' Calculate Time
    now = Digin_Fifo_Read_Timer() + zwei31
    ' get timestamp between 1 and 2^32
    delta_t = now - before 
    If (delta_t <= 0) Then ' avoid phase slips
      delta_t = now - before + zwei32
    endif
    time = time + delta_t * takt ' norm with 10ns
    before = now
  
    ' Write to FIFO
    ' Value = SUM / N
    Data_1 = mean1/count
    Data_2 = mean2/count
    Data_3 = X1/count
    Data_4 = X2/count
    Data_5 = Y1/count
    Data_6 = Y2/count
    Data_8 = trigger
    Data_9 = time
    
    ' Reset Values and Counter
    mean1 = 0.0 : X1 = 0.0 : Y1 = 0.0
    mean2 = 0.0 : X2 = 0.0 : Y2 = 0.0
    count = 0
      
  endif
  
  ' Increase Counter
  Inc(count) ' count = count + 1
