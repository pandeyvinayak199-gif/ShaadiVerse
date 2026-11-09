"""Validation for guest family RSVPs, accommodation requests and organiser limits."""
from datetime import date
import re
DEFAULT_LIMITS={'defaultPlusOnes':0,'maxPlusOnes':20,'maxFamilyMembers':21,'maxRooms':10}
DIETS=['Veg','Non-veg','Jain','Vegan','Allergies']
def integer(value,low,high):
 if isinstance(value,bool) or not re.fullmatch(r'\d+',str(value)):raise ValueError('Enter a whole number.')
 n=int(value)
 if not low<=n<=high:raise ValueError('Number is outside the allowed limit.')
 return n
def string(value,maximum=100,required=False):
 if not isinstance(value,str) or len(value)>maximum or (required and not value.strip()):raise ValueError('Please check your details.')
 return value.strip()
def limits(event):return {**DEFAULT_LIMITS,**event.get('guestLimits',{})}
def validate_limits(data):
 if not isinstance(data,dict):raise ValueError('Check limit settings.')
 result={k:integer(data.get(k),0 if k!='maxFamilyMembers' else 1,200 if k=='maxRooms' else 101 if k=='maxFamilyMembers' else 100) for k in DEFAULT_LIMITS}
 if result['defaultPlusOnes']>result['maxPlusOnes'] or result['maxPlusOnes']>=result['maxFamilyMembers']:raise ValueError('Family size must allow the guest plus their plus-ones.')
 return result
def allowance(guest,event):
 l=limits(event)
 return min(guest.get('plusOnes',l['defaultPlusOnes']),l['maxPlusOnes'],l['maxFamilyMembers']-1)
def profile(data,guest,event,timeline,hotels):
 l=limits(event);people=data.get('familyMembers')
 if not isinstance(people,list) or not 1<=len(people)<=min(l['maxFamilyMembers'],allowance(guest,event)+1):raise ValueError('Family size exceeds your invitation allowance.')
 members=[]
 for person in people:
  if not isinstance(person,dict) or person.get('diet') not in DIETS:raise ValueError('Choose a dietary preference for each person.')
  members.append({'name':string(person.get('name'),80,True),'diet':person['diet'],'origin':string(person.get('origin',''),100),'dietNotes':string(person.get('dietNotes',''),200)})
 attendance=data.get('eventAttendance');valid={str(t['id']) for t in timeline}
 if not isinstance(attendance,dict) or any(k not in valid or type(v) is not bool for k,v in attendance.items()):raise ValueError('Choose attendance for valid functions in this wedding.')
 if set(attendance)!=valid:raise ValueError('Please answer for every function. Refresh if the schedule has changed.')
 rooms=integer(data.get('roomsRequired',0),0,l['maxRooms']);arrival=string(data.get('arrivalDate',''),10);departure=string(data.get('departureDate',''),10)
 if arrival:date.fromisoformat(arrival)
 if departure:date.fromisoformat(departure)
 if arrival and departure and departure<arrival:raise ValueError('Departure must not be before arrival.')
 if rooms and not arrival:raise ValueError('Add your arrival date when requesting rooms.')
 stay_type=data.get('stayType','not-decided');hotel_id=data.get('hotelId');hotel_name=''
 if stay_type not in ['not-decided','booked-hotel','own-stay']:raise ValueError('Choose a stay option.')
 if stay_type=='booked-hotel':
  hotel=next((h for h in hotels if str(h['id'])==str(hotel_id)),None)
  if not hotel:raise ValueError('Choose a hotel booked for this wedding.')
  hotel_id=hotel['id'];hotel_name=hotel['name']
 elif stay_type=='own-stay':hotel_id=None;hotel_name=string(data.get('stayName',''),150,True)
 else:hotel_id=None
 attending=any(attendance.values());plus=len(members)-1 if attending else 0
 return {'familyMembers':members,'familyCount':len(members),'attendingPlusOnes':plus,'eventAttendance':{k:{'attending':v,'plusOnes':plus if v else 0} for k,v in attendance.items()},'events':[t['name'] for t in timeline if attendance[str(t['id'])]],'status':'Confirmed' if attending else 'Declined','diet':members[0]['diet'],'comingFrom':string(data.get('comingFrom',''),100),'roomsRequired':rooms,'arrivalDate':arrival,'departureDate':departure,'stayType':stay_type,'hotelId':hotel_id,'hotelName':hotel_name,'roomNumber':string(data.get('roomNumber',''),40)}
def vendor_details(data):
 upi=string(data.get('upiId',''),150)
 if upi and not re.fullmatch(r'[A-Za-z0-9._-]{2,100}@[A-Za-z0-9.-]{2,40}',upi):raise ValueError('Enter a valid UPI ID.')
 return {'upiId':upi,'payeeName':string(data.get('payeeName',''),100),'bankName':string(data.get('bankName',''),100),'accountLast4':string(data.get('accountLast4',''),4),'ifsc':string(data.get('ifsc',''),11),'paymentNotes':string(data.get('paymentNotes',''),300)}
