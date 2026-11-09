import concurrent.futures
from test_workflows import WorkflowCase
import server

class GuestPlanning(WorkflowCase):
 def prepare(self):
  self.owner=self.account();self.eid=self.event(self.owner);self.gid=self.guest(self.owner)
  with server.conn(True) as c:
   g=server.rows('guests',self.eid,c)[0];g['plusOnes']=3;server.update(c,'guests',g,self.eid)
  self.hotel=self.req('save',{'kind':'hotels','item':{'name':'Guest hotel','address':'Jaipur','rooms':10,'assigned':0,'checkin':'14:00'}},self.owner)[1]['id']
  self.req('save',{'kind':'timeline','item':{'name':'Mehendi','date':'2027-02-10','time':'15:00','venue':'Garden','dress':'Green'}},self.owner)
  self.req('save',{'kind':'timeline','item':{'name':'Reception','date':'2027-02-13','time':'18:00','venue':'Hall','dress':'Formal'}},self.owner)
  self.guest_cookie=self.account('9777777700','Family guest');self.req('events/select',{'eventId':self.eid},self.guest_cookie)
  self.timeline=self.req('state',cookie=self.guest_cookie)[1]['timeline']
 def profile(self):
  return {'familyMembers':[{'name':'Primary','diet':'Veg','origin':'Delhi'},{'name':'Partner','diet':'Jain','origin':'Mumbai','dietNotes':'No onion'}],'eventAttendance':{str(t['id']):i!=1 for i,t in enumerate(self.timeline)},'comingFrom':'Delhi','roomsRequired':2,'arrivalDate':'2027-02-10','departureDate':'2027-02-14','stayType':'booked-hotel','hotelId':self.hotel,'roomNumber':'104','consent':True}
 def test_family_events_hotel_and_privacy(self):
  self.prepare();data=self.req('state',cookie=self.guest_cookie)[1];self.assertEqual(len(data['timeline']),3);self.assertEqual(data['hotelOptions'][0]['name'],'Guest hotel');self.assertNotIn('rooms',data['hotelOptions'][0]);self.assertNotIn('guests',data['hotelOptions'][0]);self.assertNotIn('budget',data['event'][0])
  status,data,_=self.req('guest-profile',self.profile(),self.guest_cookie);self.assertEqual(status,200,data)
  guest=self.req('state',cookie=self.guest_cookie)[1]['guests'][0];self.assertEqual(guest['familyCount'],2);self.assertEqual(guest['attendingPlusOnes'],1);self.assertEqual(guest['hotelName'],'Guest hotel');self.assertEqual(guest['roomNumber'],'104');self.assertEqual(guest['familyMembers'][1]['diet'],'Jain');self.assertEqual(guest['eventAttendance'][str(self.timeline[1]['id'])],{'attending':False,'plusOnes':0})
  self.assertEqual(self.req('state',cookie=self.owner)[1]['guests'][0]['roomsRequired'],2)
  no=self.profile();no['eventAttendance']={str(t['id']):False for t in self.timeline};self.assertEqual(self.req('guest-profile',no,self.guest_cookie)[0],200);guest=self.req('state',cookie=self.guest_cookie)[1]['guests'][0];self.assertEqual(guest['status'],'Declined');self.assertEqual(guest['attendingPlusOnes'],0)
 def test_invalid_profile_and_scope(self):
  self.prepare()
  for field,value in [('familyMembers',[{'name':'X','diet':'Veg'}]*5),('roomsRequired',11),('hotelId',999999),('departureDate','2027-01-01'),('eventAttendance',{'9999':True}),('consent',False)]:
   body=self.profile();body[field]=value;self.assertEqual(self.req('guest-profile',body,self.guest_cookie)[0],400,(field,value))
  self.assertEqual(self.req('guest-profile',self.profile(),self.owner)[0],403)
  body=self.profile();body['familyMembers'][0]['diet']='Invalid';self.assertEqual(self.req('guest-profile',body,self.guest_cookie)[0],400)
  body=self.profile();body['stayType']='own-stay';body['stayName']='Family house';self.assertEqual(self.req('guest-profile',body,self.guest_cookie)[0],200)
 def test_coorganiser_limits_and_permissions(self):
  self.prepare();self.req('save',{'kind':'members','item':{'name':'Planner','phone':'9666666600','role':'Co-Organiser','permissions':['guests','timeline','hotels']}},self.owner);co=self.account('9666666600')
  limits={'defaultPlusOnes':1,'maxPlusOnes':3,'maxFamilyMembers':4,'maxRooms':2};body={'limits':limits,'guests':[{'id':self.gid,'plusOnes':1}]}
  self.assertEqual(self.req('guest-limits',body,co)[0],200);self.assertEqual(self.req('state',cookie=self.guest_cookie)[1]['guestAllowance'],1)
  self.assertEqual(self.req('guest-profile',self.profile(),self.guest_cookie)[0],200)
  body['guests'][0]['plusOnes']=0;self.assertEqual(self.req('guest-limits',body,co)[0],409)
  self.assertEqual(self.req('guest-limits',body,self.guest_cookie)[0],403)
  body['guests']=[{'id':999999,'plusOnes':0}];self.assertEqual(self.req('guest-limits',body,co)[0],404)
  self.assertEqual(self.req('save',{'kind':'timeline','item':{'name':'New function','date':'2027-02-11','time':'09:00','venue':'Garden'}},co)[0],200)
  body['guests']=[];body['limits']['maxRooms']=1;self.assertEqual(self.req('guest-limits',body,co)[0],409)
 def test_legacy_rsvp_cannot_bypass_limits(self):
  self.prepare();self.req('guest-limits',{'limits':{'defaultPlusOnes':0,'maxPlusOnes':1,'maxFamilyMembers':2,'maxRooms':1}},self.owner)
  self.assertEqual(self.req('rsvp',{'status':'Confirmed','plusOnes':2,'consent':True},self.guest_cookie)[0],400)

class VendorPayments(WorkflowCase):
 def prepare(self):
  self.owner=self.account();self.eid=self.event(self.owner);self.premium(self.eid)
  self.vid=self.req('save',{'kind':'vendors','item':{'name':'Photo team','quote':1000,'paid':100,'status':'Booked'}},self.owner)[1]['id']
  self.req('save',{'kind':'members','item':{'name':'Finance','phone':'9666666600','role':'Finance Team'}},self.owner);self.finance=self.account('9666666600')
 def payment(self,amount=100):return {'vendorId':self.vid,'amount':amount,'method':'UPI','reference':'receipt-1','requestId':'request-1','confirmed':True}
 def test_finance_details_upi_and_manual_record_idempotency(self):
  self.prepare();self.assertEqual(len(self.req('state',cookie=self.finance)[1]['vendors']),1)
  self.assertEqual(self.req('vendor-payments/prepare',{'vendorId':self.vid,'amount':100},self.finance)[0],409)
  self.assertEqual(self.req('vendor-payments/details',{'vendorId':self.vid,'upiId':'photos@bank','payeeName':'Photo team'},self.finance)[0],200)
  status,data,_=self.req('vendor-payments/prepare',{'vendorId':self.vid,'amount':900},self.finance);self.assertEqual(status,200);self.assertTrue(data['uri'].startswith('upi://pay?'));self.assertTrue(data['demo'])
  body=self.payment(900);self.assertEqual(self.req('vendor-payments/record',body,self.finance)[0],200);self.assertTrue(self.req('vendor-payments/record',body,self.finance)[1]['replayed'])
  state=self.req('state',cookie=self.finance)[1];self.assertEqual(state['vendors'][0]['paid'],1000);self.assertEqual(len(state['vendor_payments']),1);self.assertEqual(state['vendor_payments'][0]['status'],'Recorded manually')
 def test_limits_roles_cross_event_and_double_payment(self):
  self.prepare()
  for amount in [0,-1,1000]:self.assertEqual(self.req('vendor-payments/record',self.payment(amount),self.finance)[0],400)
  no=self.payment();no['confirmed']=False;self.assertEqual(self.req('vendor-payments/record',no,self.finance)[0],400)
  with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda _:self.req('vendor-payments/record',self.payment(),self.finance)[0],range(2)))
  self.assertEqual(results,[200,200]);self.assertEqual(self.req('state',cookie=self.finance)[1]['vendors'][0]['paid'],200)
  other=self.account('9888888801');self.event(other);self.assertEqual(self.req('vendor-payments/details',{'vendorId':self.vid},other)[0],404)
  self.req('save',{'kind':'members','item':{'name':'Planner','phone':'9666666611','role':'Co-Organiser','permissions':['tasks']}},self.owner);co=self.account('9666666611');self.assertEqual(self.req('vendor-payments/record',self.payment(),co)[0],403)
