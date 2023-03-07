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
'''
''' Important!!! compile as process nr. 10!
'''

#Include ADwinGoldII.inc

#Define Buffersize 800000                 ' Anzahl der Werte über die gemittelt wird (10^6 funktioniert nicht)
Dim Data_9[Buffersize] as Float as FIFO   ' time
Dim Data_1[Buffersize] as Float as FIFO   ' Ch1
Dim Data_2[Buffersize] as Float as FIFO   ' Ch2
Dim Data_3[Buffersize] as Float as FIFO   ' Ch3
Dim Data_4[Buffersize] as Float as FIFO   ' Ch4
  
Dim c1, c2, c3, c4 as Float
Dim count, now, before as Long
Dim time, delta_t as Float

Init:
  FIFO_Clear(9)
  FIFO_Clear(1)
  FIFO_Clear(2)
  FIFO_Clear(3)
  FIFO_Clear(4)
  
  ' Min ProcessDelay that is Prime
  ProcessDelay = 3137 ' 10ns
  
  ' Range Pattern
  Par_1 = 00b
  Par_2 = 00b
  Par_3 = 00b
  Par_4 = 00b
    
  ' Voltage Ranges
  FPar_1 = 20
  FPar_2 = 20
  FPar_3 = 20
  FPar_4 = 20
  
  ' Averaging Factor  
  Par_20  = 10
  
  ' Initialize Variables
  c1 = 0.0 : c2 = 0.0 : c3 = 0.0 : c4 = 0.0
  count = 0 : time = 0 : now = 0
  before = Digin_Fifo_Read_Timer()+2147483648
  
EVENT:
  ' Calculation of Averaging
  If (count >= Par_20) Then
    
    If (Par_10 = 1) Then
      FIFO_Clear(9)
      FIFO_Clear(1)
      FIFO_Clear(2)
      FIFO_Clear(3)
      FIFO_Clear(4)
      Par_10 = 0
    endif
      
    ' Calculate Time
    now = Digin_Fifo_Read_Timer()+2147483648 'get timestamp between 1 and 2^32
    delta_t = now - before 
    If (delta_t <= 0) Then ' avoid phase slips
      delta_t = now-before+4294967296
    endif
    time = time + (delta_t)/10^8 ' norm with 10ns
    before = now
  
    ' Write to FIFO
    Data_9 = time
    Data_1 = c1/count
    Data_2 = c2/count
    Data_3 = c3/count
    Data_4 = c4/count
    ' Value = SUM / N
      
    ' Reset Values and Counter
    c1 = 0 : c2 = 0 : c3 = 0 : c4 = 0
    count = 0
      
  endif
  
  ' Increase Counter
  Inc(count) ' count = count + 1
  
  ' Convert Analog to Digital
  ' Gold-HW II p.78
  ' Value = ( SUM / N - ( bits / 2 ) ) / bits * Range
  ' p.15 ADwin Gold II Handbuch
  
  ' REM Multiplexer setzen: ADC1 auf Kanal 1, ADC2 auf Kanal 2
  Set_Mux1((000b | shift_left(Par_1,3))) 'Multiplexer 1 auf ch 1 (1st ch row 1)
  Set_Mux2((000b | shift_left(Par_2,3))) 'Multiplexer 2 auf ch 2 (1st ch row 2)
  ' Rem IO-Zugriff für 2 µs (MUX-Einschwingzeit) unterbrechen
  IO_SLEEP(200) ' waits additional 1.5us for musker to be finished
  ' Rem Wartezeit nutzen (nicht für Zugriffe auf IOs oder Rem ext. Speicher)
    
  ' Rem ...
  Start_Conv(11b) 'Wandlung für beide ADC starten
  Wait_EOC(11b) 'Ende der Wandlungen abwarten
  c1 = c1 + (Read_ADC24(1)-8388608)/16777216*FPar_1 'ch1
  c2 = c2 + (Read_ADC24(2)-8388608)/16777216*FPar_2 'ch2
    
  ' REM Multiplexer setzen: ADC1 auf Kanal 3, ADC2 auf Kanal 4
  Set_Mux1((001b | shift_left(Par_1,3))) 'Multiplexer 1 auf ch 3 (2st ch row 1)
  Set_Mux2((001b | shift_left(Par_2,3))) 'Multiplexer 2 auf ch 4 (2st ch row 2)
  ' Rem IO-Zugriff für 2 µs (MUX-Einschwingzeit) unterbrechen
  IO_SLEEP(200) ' waits additional 2us for musker to be finished
  ' Rem Wartezeit nutzen (nicht für Zugriffe auf IOs oder Rem ext. Speicher)
    
  ' Rem ...
  Start_Conv(11b) 'Wandlung für beide ADC starten
  Wait_EOC(11b) 'Ende der Wandlungen abwarten
  c3 = c3 + (Read_ADC24(1)-8388608)/16777216*FPar_3 'ch3
  c4 = c4 + (Read_ADC24(2)-8388608)/16777216*FPar_4 'ch4
