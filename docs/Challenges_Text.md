
--- Page 1 ---

Challenge  2:  AI  Service  Orchestrator  for  Informal  Economy  
Challenge  Overview  
Informal  economy,  including  plumbers,  electricians,  tutors,  beauticians,  and  home  service  
providers,
 
operates
 
largely
 
through:
 ●  WhatsApp  messages  ●  phone  calls  ●  informal  referrals  
This  results  in:  ●  inefficient  service  matching  ●  missed  opportunities  ●  lack  of  automation  ●  poor  user  experience  
At  the  same  time,  users  struggle  to  find:  ●  reliable  services  quickly  ●  availability  in  real  time  ●  trusted  providers  nearby  
Problem  Statement  
Build  an  Agentic  AI  System  that  automates  the  end-to-end  lifecycle  of  a  service  request  —  
from
 
user
 
intent
 
to
 
booking
 
and
 
follow-up.
 
Your  system  must:  1.  Understand  user  service  requests  (in  natural  language)  2.  Identify  relevant  providers  using  location/context  3.  Select  or  recommend  the  best  provider  4.  Simulate  booking  and  confirmation  5.  Handle  follow-up  interactions  6.  Show  complete  reasoning  and  workflow  execution  
  
Mandatory  Requirement:  Google  Antigravity  
Teams  MUST  use  Google  Antigravity  as  the  core  platform  to:  ●  orchestrate  agent  workflows  ●  manage  multi-step  reasoning  ●  integrate  tools  (Maps,  Search,  APIs)  ●  execute  actions  (booking,  notifications,  etc.)  
Use  of  external  LLMs  is  allowed,  but  Antigravity  must  be  central  to  system  logic  and  
orchestration
.
 
--- Page 2 ---

Example  User  Scenario  
User  input  (Roman  Urdu  /  Urdu  /  English):  
“Mujhe  kal  subah  G-13  mein  AC  technician  chahiye”  
  
Expected  Output  Service  Request:  AC  Technician  Location:  G-13  Time:  Tomorrow  morning  Recommended  Provider:  Ali  AC  Services  (2.1  km  away)  Reasoning:  Closest  available  provider  with  high  rating  Simulated  Booking:  -  Slot  booked:  10:00  AM  -  Confirmation  sent  Follow-up:  Reminder  scheduled  1  hour  before  appointment  
System  Requirements  
1.  Intent  Understanding  ●  Process  natural  language  input  ●  Support:  
§
  
Urdu  §
  
Roman  Urdu  §
  
English  ●  Extract:  
§
  
service  type  §
  
location  §
  
time  
2.  Provider  Discovery  ●  Use:  
§
  
mock  dataset  OR  §
  
Google  Maps  /  Places  APIs  ●  Identify:  
--- Page 3 ---

§
  
nearby  providers  §
  
service  category  match  
3.  Matching  &  Ranking  ●  Rank  providers  based  on:  
§
  
distance  §
  
availability  §
  
rating  (simulated  or  real)  ●  Provide  clear  reasoning  for  selection  
4.  Decision  &  Recommendation  ●  Select  best  provider  OR  show  top  options  ●  Explain  decision  in  simple  terms  
5.  Action  Simulation  (CRITICAL  REQUIREMENT)  
System  must  simulate:  ●  booking  confirmation  ●  provider  assignment  ●  scheduling  
Simulation  can  include:  ●  updating  a  mock  booking  system  ●  creating  a  confirmation  message  ●  writing  to  a  database/spreadsheet  ●  generating  a  booking  receipt  
6.  Follow-Up  Automation  ●  Simulate:  
§
  
reminders  §
  
status  updates  §
  
completion  confirmation  
7.  Agentic  Workflow  (MANDATORY)  
System  must  demonstrate:  ●  multiple  agents  OR  structured  reasoning  pipeline  ●  planning  →  decision  →  action  →  follow-up  ●  traceable  logs  of:  
§
  
decisions  §
  
tool  usage  §
  
action  execution  
--- Page 4 ---

Deliverables  
1.  Working  Prototype  with  Mobile  App  (MUST)  and  Web  App  (Optional)  
2.  Demo  Video  (3–5  minutes)  
Must  clearly  show:  ●  user  input  ●  system  understanding  ●  provider  matching  ●  booking  simulation  ●  follow-up  workflow  
3.  Agent  Trace  /  Logs  ●  reasoning  steps  ●  agent  interactions  ●  action  execution  logs  
4.  Documentation  (README)  
Include:  ●  system  architecture  ●  how  Antigravity  is  used  ●  APIs/tools  used  ●  assumptions  and  limitations  
  
 Evaluation  Criteria  
1.  Use  of  Google  Antigravity  —  25%  ●  Core  orchestration  handled  via  Antigravity  ●  Effective  use  of  tools  (Maps,  APIs)  ●  Demonstrates  planning  +  execution  
2.  Agentic  Reasoning  &  Workflow  —  20%  ●  Multi-step  reasoning  ●  Logical  flow  from  request  →  decision  →  action  ●  Evidence  of  autonomy  
3.  Matching  Quality  &  Decision  Logic  —  20%  ●  Relevant  provider  selection  ●  Clear  ranking  criteria  ●  Strong  reasoning  behind  decisions  
4.  Action  Simulation  &  Execution  —  15%  
--- Page 5 ---

●  Booking  process  realistically  simulated  ●  Clear  system  state  change  (confirmation,  scheduling)  ●  End-to-end  workflow  demonstrated  
5.  Technical  Implementation  —  10%  ●  Clean  architecture  ●  API/tool  integration  ●  Robust  handling  of  edge  cases  
6.  Innovation  &  UX  —  10%  ●  Creative  approach  ●  Intuitive  interface  ●  Clear  and  engaging  demo  
Important  Guidelines  ●  This  is  NOT  a  simple  listing  or  booking  app  ●  Focus  on  agentic  automation,  not  UI  complexity  ●  At  least  one  booking  must  be  simulated  end-to-end  ●  Must  demonstrate  reasoning  +  decision-making  ●  Use  mock  data  if  real  APIs  are  unavailable  ●  Avoid  use  of  real  personal/sensitive  data  
  
   
  