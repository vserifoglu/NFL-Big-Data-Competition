# Competition FAQ: Data Clarifications

## Q1: Clarification on output data
**Question**:  
The output data, is this the data while the ball is explicitly in the air or is it the rest of the play? Is the time the receiver catches the ball the last frame in the output file or does the receiver catch the ball somewhere during the frames in the output file?

**Answer**:  
The output data is explicitly when the ball is in the air.  
The last frame of the output data is when the pass arrives (pass does not always result in a catch).

---

## Q2: Quick Question about Frames
**Question**:  
I hope this wasn't already covered somewhere in the data overview and I simply missed it, but I couldn't find any information about how much time elapses between each frame in the input and output files. Does the data contain a frame every second, a frame every half second, a frame every tenth of a second? Again, apologize if the information is actually somewhere and I just didn't see it.

**Answer**:  
Great question — a tenth of a second.

---

## Q3: Pass Forward Frame
**Question**:  
I was wondering which frame is the pass forward moment. Is it the last frame in the input data, or the first frame in the output data?

**Answer**:  
It is the first frame of the output.

---

## Q4: Competition focus and data split before and while the ball is in the air
**Question**:  
In this competition we have a lot of data from before the pass is thrown and a lot less data while the ball is airborne, specifically we have only (x,y) tuple for 5+ frames for 1 receiver and 0–8 defenders. Of course the topic is "understand player movement while the ball is in the air."

Now here is my question: Is the focus on what player movement before the throw tells us about movement while the ball is in the air, mainly use data while the ball is airborne to understand that specific aspect of the play, or are we more or less free to do whatever analysis we want as long as it's using this year's (tracking) data?

**Answer**:  
Ultimately, the focus is on the relationship between:
- Contextual information in the supplemental data
- Player movement before the ball is thrown
- Player movement after the ball is thrown

However, that does not mean your project must be a prediction of player x–y coordinates while the ball is in the air (goal of the prediction contest). You are free to focus on specific positions, specific situations in a game, or define "player movement" as something other than x–y coordinates (or anything else that relates to player movement with ball in air).

---

## Q5: Clarification on output data (similar to Q1)
**Question**:  
The output data, is this the data while the ball is explicitly in the air or is it the rest of the play? Is the time the receiver catches the ball the last frame in the output file or does the receiver catch the ball somewhere during the frames in the output file?

**Answer**:  
The output data is explicitly when the ball is in the air.  
The last frame of the output data is when the pass arrives (pass does not always result in a catch).


Design limitations: 

By design, the output data excludes defenders more than ~8 yards from the landing point, which encodes an assumption that such players have negligible direct impact on the catch or immediate YAC.