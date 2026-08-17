// flows.js - All conversation flows and button interactions

// General Information Fields for all combo packages
export const generalInfoFields = [
  { name: 'title', label: 'Title', type: 'select', options: ['Mr', 'Mrs', 'Ms', 'Miss', 'Dr'], required: true },
  { name: 'first_name', label: 'First Name', type: 'text', placeholder: 'John', required: true },
  { name: 'last_name', label: 'Last Name', type: 'text', placeholder: 'Doe', required: true },
  { name: 'email', label: 'Email Address', type: 'email', placeholder: 'john@example.com', required: true },
  { name: 'country_code', label: 'Country Code', type: 'select', options: ['+1', '+44', '+91', '+33', '+49', '+39', '+34', '+351', '+41'], required: true },
  { name: 'mobile', label: 'Mobile Number', type: 'tel', placeholder: '1234567890', required: true },
  { name: 'adults', label: 'Number of Adults', type: 'number', placeholder: '2', required: true },
  { name: 'kids', label: 'Number of Kids', type: 'number', placeholder: '0', required: false },
  { name: 'kids_ages', label: 'Ages of Kids (separated by comma)', type: 'text', placeholder: 'e.g., 5, 8', required: false }
];

export const flows = {
  greeting: {
    message: 'Hello 👋\n\nWelcome to SchengenVisaItinerary\n\nHow can we help you today?',
    buttons: [
      { label: '🛂 Visa Services', action: 'visaServices' },
      { label: '📋 Travel Documentation for Visa Process', action: 'travelDocsForVisa' },
      { label: '🏖️ Holiday Packages', action: 'holidayPackages' }
    ]
  },
  
  visaServices: {
    message: 'What would you like to do for visa services? 🛂',
    buttons: [
      { label: '💰 Get Visa Price', action: 'visaPrice' },
      { label: '📄 Know Visa Process', action: 'visaProcess' },
      { label: '📝 Apply for Visa', action: 'visaFormModal' },
      { label: '❓ Visa FAQ', action: 'visaFAQ' }
    ]
  },
  
  visaFormModal: {
    action: 'showForm',
    message: '📝 Visa Application Form',
    fields: [
      ...generalInfoFields,
      { name: 'visa_destination', label: 'Destination Country', type: 'text', placeholder: 'e.g., France, Germany', required: true },
      { name: 'visa_type', label: 'Visa Type', type: 'select', options: ['Tourist', 'Business', 'Student', 'Work'], required: true },
      { name: 'visa_start_date', label: 'Travel Start Date', type: 'date', required: true },
      { name: 'visa_end_date', label: 'Travel End Date', type: 'date', required: true },
      { name: 'visa_urgency', label: 'Processing Type', type: 'select', options: ['Normal', 'Urgent'], required: true }
    ],
    submitLabel: 'Submit Application',
    nextAction: 'visaSummary'
  },
  
  visaSummary: {
    type: 'summary',
    message: '✅ Thank you!\n\nHere\'s a summary of your visa request:',
    buttons: [
      { label: '💰 Get Price', action: 'visaPrice' },
      { label: '📝 Proceed with Booking', action: 'bookingConfirm' }
    ]
  },
  
  bookingConfirm: {
    message: '🎉 Excellent! Your visa application has been submitted.\n\nWe\'ll contact you within 24 hours with pricing and next steps. Thank you! 🙏',
    buttons: [
      { label: '🛂 New Visa Request', action: 'visaServices' },
      { label: '✈️ Other Services', action: 'travelDocsForVisa' },
      { label: '❌ End Chat', action: 'endChat' }
    ]
  },
  
  visaPrice: {
    message: '💰 Visa Pricing\n\nSchengen Visa Costs:\n• Tourist: €80\n• Business: €100\n• Student: €60\n• Work: €120\n\nProcessing fees apply based on urgency.\n\nContact us for exact quote! 📞',
    buttons: [
      { label: '📝 Apply Now', action: 'visaFormModal' },
      { label: '📞 Contact Us', action: 'callSupport' }
    ]
  },
  
  visaProcess: {
    message: '📄 Schengen Visa Process\n\n1️⃣ Submit Application\n2️⃣ Document Verification (3-5 days)\n3️⃣ Visa Interview (if needed)\n4️⃣ Decision & Stamping (7-15 days)\n5️⃣ Passport Collection\n\nNormal processing: 15 days\nUrgent processing: 3-5 days',
    buttons: [
      { label: '📝 Apply Now', action: 'visaFormModal' },
      { label: '📞 Contact Us', action: 'callSupport' }
    ]
  },
  
  visaFAQ: {
    message: '❓ Frequently Asked Questions\n\n• Valid passport: Yes, required\n• Insurance: Yes, €30,000 minimum\n• Bank statements: Yes, 6 months\n• Hotel bookings: Yes, required\n• Travel insurance: Yes, Schengen compliant\n\nHave more questions?',
    buttons: [
      { label: '📝 Apply Now', action: 'visaFormModal' },
      { label: '📞 Contact Us', action: 'callSupport' }
    ]
  },
  
  travelDocsForVisa: {
    message: '📋 Travel Documentation for Visa Process\n\nWhich service do you need? ✈️',
    buttons: [
      { label: '✈️ Flight Booking', action: 'flightOptions' },
      { label: '🏨 Hotel Booking', action: 'hotelOptions' },
      { label: '🛡️ Travel Insurance', action: 'insuranceOptions' },
      { label: '📦 Combo Package', action: 'comboOptions' }
    ]
  },
  
  // ======== FLIGHT OPTIONS FLOW ========
  flightOptions: {
    message: '✈️ Flight Booking for Visa\n\nChoose an option:',
    buttons: [
      { label: '💰 Flight Price for Visa', action: 'flightPriceForVisa' },
      { label: '📝 Book Flight Now', action: 'flightFormModal' },
      { label: '❓ Flight FAQ', action: 'flightFAQ' }
    ]
  },
  
  flightPriceForVisa: {
    message: '💰 Flight Pricing for Visa Applications\n\n• Basic itinerary (for visa): €25\n• Confirmed booking (refundable): €50-150\n• Flexible ticket: €150-300\n\nVisa-verified flight documents included! ✅',
    buttons: [
      { label: '📝 Book Now', action: 'flightFormModal' },
      { label: '❓ FAQ', action: 'flightFAQ' }
    ]
  },
  
  flightFAQ: {
    message: '❓ Flight Booking FAQ for Visa\n\n• Do I need a flight ticket for visa? Yes, confirmed or reserved\n• Are your tickets refundable? Yes, we provide visa-friendly options\n• How long is the booking valid? 30 days minimum\n• Do embassies accept your documents? 100% acceptance rate\n\nNeed more info?',
    buttons: [
      { label: '💰 Get Price', action: 'flightPriceForVisa' },
      { label: '📝 Book Now', action: 'flightFormModal' }
    ]
  },
  
  flightFormModal: {
    action: 'showForm',
    message: '✈️ Flight Booking Form',
    fields: [
      ...generalInfoFields,
      { name: 'flight_depart', label: 'Departure City', type: 'text', placeholder: 'e.g., New York', required: true },
      { name: 'flight_arrival', label: 'Arrival City', type: 'text', placeholder: 'e.g., Paris', required: true },
      { name: 'flight_date', label: 'Departure Date', type: 'date', required: true },
      { name: 'flight_return', label: 'Return Date (if round-trip)', type: 'date', required: false },
      { name: 'flight_type', label: 'Trip Type', type: 'select', options: ['One-way', 'Round-trip'], required: true },
      { name: 'flight_budget', label: 'Budget Range', type: 'select', options: ['Budget (€50-150)', 'Standard (€150-300)', 'Premium (€300+)'], required: false }
    ],
    submitLabel: 'Book Flight',
    nextAction: 'flightSummary'
  },
  
  flightSummary: {
    type: 'summary',
    message: '✅ Flight details recorded!\n\nWe\'ll send you flight options shortly.',
    buttons: [
      { label: '💰 Get Price', action: 'flightPrice' },
      { label: '📝 Book Now', action: 'flightBook' }
    ]
  },
  
  flightPrice: {
    message: '💰 Flight Pricing\n\nEstimated costs vary by airline:\n• Budget Airlines: €50-150\n• Full Service: €150-400\n• Premium: €400+\n\nWe find the best deals for you! ✨',
    buttons: [
      { label: '📝 Book Now', action: 'flightBook' },
      { label: '🏨 Hotel', action: 'hotelOptions' }
    ]
  },
  
  flightBook: {
    message: '🎉 Flight booking in progress!\n\nOur team will contact you with flight options and best prices.',
    buttons: [
      { label: '✈️ New Flight', action: 'flightFormModal' },
      { label: '🏨 Add Hotel', action: 'hotelFormModal' },
      { label: '🛂 Add Visa', action: 'visaFormModal' },
      { label: '❌ End Chat', action: 'endChat' }
    ]
  },
  
  // ======== HOTEL OPTIONS FLOW ========
  hotelOptions: {
    message: '🏨 Hotel Booking for Visa\n\nChoose an option:',
    buttons: [
      { label: '💰 Hotel Price for Visa', action: 'hotelPriceForVisa' },
      { label: '📝 Book Hotel Now', action: 'hotelFormModal' },
      { label: '❓ Hotel FAQ', action: 'hotelFAQ' }
    ]
  },
  
  hotelPriceForVisa: {
    message: '💰 Hotel Pricing for Visa Applications\n\n• Basic reservation (for visa): €15\n• Confirmed booking (refundable): €30-80/night\n• 4-star verified hotel: €80-150/night\n\nVisa-acceptable hotel documents included! ✅',
    buttons: [
      { label: '📝 Book Now', action: 'hotelFormModal' },
      { label: '❓ FAQ', action: 'hotelFAQ' }
    ]
  },
  
  hotelFAQ: {
    message: '❓ Hotel Booking FAQ for Visa\n\n• Do I need hotel booking for visa? Yes, confirmed reservation required\n• Are bookings refundable? Yes, we provide visa-compliant options\n• Do you cover entire stay? Yes, for all Schengen countries\n• Embassy acceptance? 100% acceptance guaranteed\n\nNeed more info?',
    buttons: [
      { label: '💰 Get Price', action: 'hotelPriceForVisa' },
      { label: '📝 Book Now', action: 'hotelFormModal' }
    ]
  },
  
  hotelFormModal: {
    action: 'showForm',
    message: '🏨 Hotel Booking Form',
    fields: [
      ...generalInfoFields,
      { name: 'hotel_city', label: 'Destination City', type: 'text', placeholder: 'e.g., Paris', required: true },
      { name: 'hotel_checkin', label: 'Check-in Date', type: 'date', required: true },
      { name: 'hotel_checkout', label: 'Check-out Date', type: 'date', required: true },
      { name: 'hotel_rooms', label: 'Number of Rooms', type: 'select', options: ['1 Room', '2 Rooms', '3+ Rooms'], required: true },
      { name: 'hotel_type', label: 'Hotel Type', type: 'select', options: ['Budget', '3-Star', '4-Star', '5-Star'], required: false }
    ],
    submitLabel: 'Book Hotel',
    nextAction: 'hotelSummary'
  },
  
  hotelSummary: {
    type: 'summary',
    message: '✅ Hotel details recorded!\n\nSearching best hotels for you...',
    buttons: [
      { label: '💰 Get Price', action: 'hotelPrice' },
      { label: '📝 Book Now', action: 'hotelBook' }
    ]
  },
  
  hotelPrice: {
    message: '💰 Hotel Pricing\n\nAverage rates per night:\n• Budget: €40-80\n• 3-Star: €80-150\n• 4-Star: €150-250\n• 5-Star: €250+\n\nWe compare all options! 🏆',
    buttons: [
      { label: '📝 Book Now', action: 'hotelBook' },
      { label: '🛡️ Insurance', action: 'insuranceOptions' }
    ]
  },
  
  hotelBook: {
    message: '🎉 Hotel booking submitted!\n\nWe\'ll send you curated hotel options with best prices.',
    buttons: [
      { label: '🏨 New Hotel', action: 'hotelFormModal' },
      { label: '✈️ Add Flight', action: 'flightFormModal' },
      { label: '🛡️ Add Insurance', action: 'insuranceFormModal' },
      { label: '❌ End Chat', action: 'endChat' }
    ]
  },
  
  // ======== INSURANCE OPTIONS FLOW ========
  insuranceOptions: {
    message: '🛡️ Travel Insurance for Visa\n\nChoose an option:',
    buttons: [
      { label: '💰 Insurance Price for Visa', action: 'insurancePriceForVisa' },
      { label: '📝 Get Insurance Now', action: 'insuranceFormModal' },
      { label: '❓ Insurance FAQ', action: 'insuranceFAQ' }
    ]
  },
  
  insurancePriceForVisa: {
    message: '💰 Travel Insurance Pricing\n\n• Basic Schengen (€30K coverage): €15/week\n• Comprehensive (€50K coverage): €25/week\n• Family plan (2 adults + kids): €40/week\n\nSchengen-compliant certificates provided! ✅',
    buttons: [
      { label: '📝 Buy Now', action: 'insuranceFormModal' },
      { label: '❓ FAQ', action: 'insuranceFAQ' }
    ]
  },
  
  insuranceFAQ: {
    message: '❓ Travel Insurance FAQ for Visa\n\n• Is insurance mandatory for Schengen? Yes, minimum €30,000 coverage\n• COVID coverage included? Yes, in comprehensive plans\n• How quickly do I get certificate? Within 1 hour\n• Do embassies accept? 100% Schengen compliant\n\nNeed more info?',
    buttons: [
      { label: '💰 Get Price', action: 'insurancePriceForVisa' },
      { label: '📝 Buy Now', action: 'insuranceFormModal' }
    ]
  },
  
  insuranceFormModal: {
    action: 'showForm',
    message: '🛡️ Travel Insurance Application',
    fields: [
      ...generalInfoFields,
      { name: 'insurance_date_of_birth', label: 'Date of Birth (as per passport)', type: 'date', required: true },
      { name: 'insurance_passport_number', label: 'Passport Number', type: 'text', placeholder: 'AB1234567', required: true },
      { name: 'insurance_passport_expiry', label: 'Passport Expiry Date', type: 'date', required: true },
      { name: 'insurance_start_date', label: 'Insurance Start Date', type: 'date', required: true },
      { name: 'insurance_end_date', label: 'Insurance End Date', type: 'date', required: true },
      { name: 'insurance_type', label: 'Insurance Type', type: 'select', options: ['Medical', 'Comprehensive', 'Trip', 'Backpacker'], required: true },
      { name: 'insurance_coverage', label: 'Coverage Type', type: 'select', options: ['Standard', 'Premium'], required: true }
    ],
    submitLabel: 'Get Insurance Quote',
    nextAction: 'insuranceSummary'
  },
  
  insuranceSummary: {
    type: 'summary',
    message: '✅ Insurance details recorded!\n\nPerfect for your trip protection.',
    buttons: [
      { label: '💰 Get Quote', action: 'insurancePrice' },
      { label: '📝 Purchase Now', action: 'insuranceBuy' }
    ]
  },
  
  insurancePrice: {
    message: '💰 Insurance Pricing\n\n• Medical: €15-30\n• Comprehensive: €30-60\n• Trip: €20-40\n• Backpacker: €10-20\n\nSchengen compliant! ✅',
    buttons: [
      { label: '📝 Purchase', action: 'insuranceBuy' },
      { label: '📦 Combo Package', action: 'comboOptions' }
    ]
  },
  
  insuranceBuy: {
    message: '🎉 Insurance added!\n\nWould you like to proceed with purchase?',
    buttons: [
      { label: '✅ Yes, Purchase', action: 'insuranceConfirm' }
    ]
  },
  
  insuranceConfirm: {
    message: '✅ Insurance purchased!\n\nYour policy details will be emailed shortly.',
    buttons: [
      { label: '✈️ Book Flight', action: 'flightFormModal' },
      { label: '🏨 Book Hotel', action: 'hotelFormModal' },
      { label: '❌ End Chat', action: 'endChat' }
    ]
  },
  
  // ======== COMBO OPTIONS FLOW ========
  comboOptions: {
    message: '📦 Combo Packages for Visa\n\nChoose an option:',
    buttons: [
      { label: '💰 Combo Price for Visa', action: 'comboPriceForVisa' },
      { label: '📝 Book Combo Now', action: 'comboPackageOptions' },
      { label: '❓ Combo FAQ', action: 'comboFAQ' }
    ]
  },
  
  comboPriceForVisa: {
    message: '💰 Combo Package Pricing\n\n• Flight + Hotel combo: €50 (save 20%)\n• Flight + Hotel + Insurance: €80 (save 25%)\n• Complete visa package: €120 (save 30%)\n\nAll documents visa-ready! ✅',
    buttons: [
      { label: '📝 Book Now', action: 'comboPackageOptions' },
      { label: '❓ FAQ', action: 'comboFAQ' }
    ]
  },
  
  comboFAQ: {
    message: '❓ Combo Package FAQ\n\n• What\'s included? All visa-required documents\n• Are all bookings refundable? Yes, visa-friendly terms\n• How many countries covered? All Schengen countries\n• Processing time? 24-48 hours for all documents\n\nNeed more info?',
    buttons: [
      { label: '💰 Get Price', action: 'comboPriceForVisa' },
      { label: '📝 Book Now', action: 'comboPackageOptions' }
    ]
  },
  
  comboPackageOptions: {
    message: '📦 Combo Packages\n\nBundle services & save up to 25%!\n\nChoose your combo:',
    buttons: [
      { label: '🛂✈️🏨 Visa + Flight + Hotel', action: 'comboVisaFlightHotelModal' },
      { label: '✈️🏨🛡️ Flight + Hotel + Insurance', action: 'comboFlightHotelInsuranceModal' },
      { label: '🛂✈️🏨🛡️ Complete Travel Package', action: 'comboCompletePackageModal' }
    ]
  },
  
  comboVisaFlightHotelModal: {
    action: 'showForm',
    message: '🛂✈️🏨 Visa + Flight + Hotel Combo',
    fields: [
      ...generalInfoFields,
      // Visa Section
      { name: 'combo_visa_destination', label: 'Visa Destination Country', type: 'text', placeholder: 'e.g., France, Germany', required: true },
      { name: 'combo_visa_type', label: 'Visa Type', type: 'select', options: ['Tourist', 'Business', 'Student', 'Work'], required: true },
      { name: 'combo_visa_start_date', label: 'Travel Start Date', type: 'date', required: true },
      { name: 'combo_visa_end_date', label: 'Travel End Date', type: 'date', required: true },
      { name: 'combo_visa_urgency', label: 'Visa Processing Type', type: 'select', options: ['Normal', 'Urgent'], required: true },
      
      // Flight Section
      { name: 'combo_flight_depart', label: 'Departure City', type: 'text', placeholder: 'e.g., New York', required: true },
      { name: 'combo_flight_arrival', label: 'Arrival City', type: 'text', placeholder: 'e.g., Paris', required: true },
      { name: 'combo_flight_date', label: 'Flight Date', type: 'date', required: true },
      { name: 'combo_flight_type', label: 'Trip Type', type: 'select', options: ['One-way', 'Round-trip'], required: true },
      
      // Hotel Section
      { name: 'combo_hotel_city', label: 'Hotel City', type: 'text', placeholder: 'e.g., Paris', required: true },
      { name: 'combo_hotel_checkin', label: 'Check-in Date', type: 'date', required: true },
      { name: 'combo_hotel_checkout', label: 'Check-out Date', type: 'date', required: true },
      { name: 'combo_hotel_rooms', label: 'Number of Rooms', type: 'select', options: ['1 Room', '2 Rooms', '3+ Rooms'], required: true },
      { name: 'combo_hotel_type', label: 'Hotel Type', type: 'select', options: ['Budget', '3-Star', '4-Star', '5-Star'], required: false }
    ],
    submitLabel: 'Proceed to Review',
    nextAction: 'comboVisaFlightHotelReview'
  },
  
  comboVisaFlightHotelReview: {
    type: 'summary',
    message: '📋 Review Your Combo Package\n\n🛂✈️🏨 Visa + Flight + Hotel\n\nPlease review your details:',
    buttons: [
      { label: '✅ Yes, Book Now', action: 'comboPaymentForm' },
      { label: '✏️ Edit Details', action: 'comboVisaFlightHotelModal' }
    ]
  },
  
  comboFlightHotelInsuranceModal: {
    action: 'showForm',
    message: '✈️🏨🛡️ Flight + Hotel + Insurance Combo',
    fields: [
      ...generalInfoFields,
      // Flight Section
      { name: 'combo_fhi_flight_depart', label: 'Departure City', type: 'text', placeholder: 'e.g., New York', required: true },
      { name: 'combo_fhi_flight_arrival', label: 'Arrival City', type: 'text', placeholder: 'e.g., Paris', required: true },
      { name: 'combo_fhi_flight_date', label: 'Flight Date', type: 'date', required: true },
      { name: 'combo_fhi_flight_return', label: 'Return Date (if round-trip)', type: 'date', required: false },
      { name: 'combo_fhi_flight_type', label: 'Trip Type', type: 'select', options: ['One-way', 'Round-trip'], required: true },
      
      // Hotel Section
      { name: 'combo_fhi_hotel_city', label: 'Hotel City', type: 'text', placeholder: 'e.g., Paris', required: true },
      { name: 'combo_fhi_hotel_checkin', label: 'Check-in Date', type: 'date', required: true },
      { name: 'combo_fhi_hotel_checkout', label: 'Check-out Date', type: 'date', required: true },
      { name: 'combo_fhi_hotel_rooms', label: 'Number of Rooms', type: 'select', options: ['1 Room', '2 Rooms', '3+ Rooms'], required: true },
      { name: 'combo_fhi_hotel_type', label: 'Hotel Type', type: 'select', options: ['Budget', '3-Star', '4-Star', '5-Star'], required: false },
      
      // Insurance Section
      { name: 'combo_fhi_insurance_type', label: 'Insurance Type', type: 'select', options: ['Medical', 'Comprehensive', 'Trip', 'Backpacker'], required: true },
      { name: 'combo_fhi_insurance_date_of_birth', label: 'Date of Birth (as per passport)', type: 'date', required: true },
      { name: 'combo_fhi_insurance_passport_number', label: 'Passport Number', type: 'text', placeholder: 'AB1234567', required: true },
      { name: 'combo_fhi_insurance_passport_expiry', label: 'Passport Expiry Date', type: 'date', required: true },
      { name: 'combo_fhi_insurance_start_date', label: 'Insurance Start Date', type: 'date', required: true },
      { name: 'combo_fhi_insurance_end_date', label: 'Insurance End Date', type: 'date', required: true },
      { name: 'combo_fhi_insurance_coverage', label: 'Coverage Type', type: 'select', options: ['Standard', 'Premium'], required: true }
    ],
    submitLabel: 'Proceed to Review',
    nextAction: 'comboFlightHotelInsuranceReview'
  },
  
  comboFlightHotelInsuranceReview: {
    type: 'summary',
    message: '📋 Review Your Combo Package\n\n✈️🏨🛡️ Flight + Hotel + Insurance\n\nPlease review your details:',
    buttons: [
      { label: '✅ Yes, Book Now', action: 'comboPaymentForm' },
      { label: '✏️ Edit Details', action: 'comboFlightHotelInsuranceModal' }
    ]
  },
  
  comboCompletePackageModal: {
    action: 'showForm',
    message: '🛂✈️🏨🛡️ Complete Travel Package',
    fields: [
      ...generalInfoFields,
      // Visa Section
      { name: 'complete_visa_destination', label: 'Visa Destination Country', type: 'text', placeholder: 'e.g., France, Germany', required: true },
      { name: 'complete_visa_type', label: 'Visa Type', type: 'select', options: ['Tourist', 'Business', 'Student', 'Work'], required: true },
      { name: 'complete_visa_start_date', label: 'Travel Start Date', type: 'date', required: true },
      { name: 'complete_visa_end_date', label: 'Travel End Date', type: 'date', required: true },
      { name: 'complete_visa_urgency', label: 'Visa Processing Type', type: 'select', options: ['Normal', 'Urgent'], required: true },
      
      // Flight Section
      { name: 'complete_flight_depart', label: 'Departure City', type: 'text', placeholder: 'e.g., New York', required: true },
      { name: 'complete_flight_arrival', label: 'Arrival City', type: 'text', placeholder: 'e.g., Paris', required: true },
      { name: 'complete_flight_date', label: 'Flight Date', type: 'date', required: true },
      { name: 'complete_flight_type', label: 'Trip Type', type: 'select', options: ['One-way', 'Round-trip'], required: true },
      
      // Hotel Section
      { name: 'complete_hotel_city', label: 'Hotel City', type: 'text', placeholder: 'e.g., Paris', required: true },
      { name: 'complete_hotel_checkin', label: 'Check-in Date', type: 'date', required: true },
      { name: 'complete_hotel_checkout', label: 'Check-out Date', type: 'date', required: true },
      { name: 'complete_hotel_rooms', label: 'Number of Rooms', type: 'select', options: ['1 Room', '2 Rooms', '3+ Rooms'], required: true },
      { name: 'complete_hotel_type', label: 'Hotel Type', type: 'select', options: ['Budget', '3-Star', '4-Star', '5-Star'], required: false },
      
      // Insurance Section
      { name: 'complete_insurance_type', label: 'Insurance Type', type: 'select', options: ['Medical', 'Comprehensive', 'Trip', 'Backpacker'], required: true },
      { name: 'complete_insurance_date_of_birth', label: 'Date of Birth (as per passport)', type: 'date', required: true },
      { name: 'complete_insurance_passport_number', label: 'Passport Number', type: 'text', placeholder: 'AB1234567', required: true },
      { name: 'complete_insurance_passport_expiry', label: 'Passport Expiry Date', type: 'date', required: true },
      { name: 'complete_insurance_start_date', label: 'Insurance Start Date', type: 'date', required: true },
      { name: 'complete_insurance_end_date', label: 'Insurance End Date', type: 'date', required: true },
      { name: 'complete_insurance_coverage', label: 'Coverage Type', type: 'select', options: ['Standard', 'Premium'], required: true }
    ],
    submitLabel: 'Proceed to Review',
    nextAction: 'comboCompletePackageReview'
  },
  
  comboCompletePackageReview: {
    type: 'summary',
    message: '📋 Review Your Complete Package\n\n🛂✈️🏨🛡️ Visa + Flight + Hotel + Insurance\n\nPlease review your details:',
    buttons: [
      { label: '✅ Yes, Book Now', action: 'comboPaymentForm' },
      { label: '✏️ Edit Details', action: 'comboCompletePackageModal' }
    ]
  },
  
  comboPaymentForm: {
    action: 'showForm',
    message: '💳 Payment Information',
    fields: [
      { name: 'payment_card_name', label: 'Cardholder Name', type: 'text', placeholder: 'John Doe', required: true },
      { name: 'payment_card_number', label: 'Card Number', type: 'text', placeholder: '1234 5678 9012 3456', required: true },
      { name: 'payment_expiry', label: 'Expiry Date', type: 'month', required: true },
      { name: 'payment_cvv', label: 'CVV', type: 'text', placeholder: '123', required: true },
      { name: 'payment_address', label: 'Billing Address', type: 'text', placeholder: '123 Main St, City, Country', required: true },
      { name: 'payment_zip', label: 'ZIP/Postal Code', type: 'text', placeholder: '12345', required: true }
    ],
    submitLabel: 'Complete Payment',
    nextAction: 'paymentConfirmation'
  },
  
  paymentConfirmation: {
    message: '✅ Payment Successful!\n\n🎉 Your booking has been confirmed!\n\n📧 A detailed confirmation with itinerary has been sent to your registered email address.\n\n📱 You will also receive SMS updates.\n\nThank you for choosing SchengenVisaItinerary! ✈️',
    buttons: [
      { label: '🛂 New Booking', action: 'greeting' },
      { label: '❌ End Chat', action: 'endChat' }
    ]
  },
  
  holidayPackages: {
    message: 'What kind of holiday are you planning? 🏖️',
    buttons: [
      { label: '🏠 Domestic Package', action: 'holidayFormModal' },
      { label: '✈️ International Package', action: 'holidayFormModal' },
      { label: '💑 Honeymoon', action: 'holidayHoneymoonModal' },
      { label: '👨‍👩‍👧‍👦 Family Trip', action: 'holidayFamilyModal' },
      { label: '🎨 Custom Package', action: 'holidayFormModal' },
      { label: '❓ Holiday FAQ', action: 'holidayFAQ' }
    ]
  },
  
  holidayFAQ: {
    message: '❓ Holiday Package FAQ\n\n• What\'s included in packages? Flights, hotels, transfers\n• Can I customize itinerary? Yes, fully customizable\n• Are meals included? As per package selected\n• Visa assistance included? Yes, we guide you\n• Payment options? Card, bank transfer, PayPal\n\nNeed more information?',
    buttons: [
      { label: '💰 Get Price', action: 'holidayPrice' },
      { label: '📝 Book Package', action: 'holidayFormModal' },
      { label: '📞 Contact Us', action: 'callSupport' }
    ]
  },
  
  holidayFormModal: {
    action: 'showForm',
    message: '🏖️ Holiday Package Form',
    fields: [
      ...generalInfoFields,
      { name: 'holiday_type', label: 'Package Type', type: 'select', options: ['Domestic', 'International', 'Custom'], required: true },
      { name: 'holiday_destination', label: 'Destination(s)', type: 'text', placeholder: 'e.g., France, Switzerland', required: true },
      { name: 'holiday_start_date', label: 'Start Date', type: 'date', required: true },
      { name: 'holiday_end_date', label: 'End Date', type: 'date', required: true },
      { name: 'holiday_budget', label: 'Budget Range', type: 'select', options: ['Budget (€800-1500)', 'Mid-range (€1500-3000)', 'Luxury (€3000+)'], required: true }
    ],
    submitLabel: 'Create Package',
    nextAction: 'holidaySummary'
  },
  
  holidayHoneymoonModal: {
    action: 'showForm',
    message: '💑 Honeymoon Package Form',
    fields: [
      ...generalInfoFields.filter(field => !field.name.includes('kids')),
      { name: 'honeymoon_destination', label: 'Destination(s)', type: 'text', placeholder: 'e.g., Paris, Rome', required: true },
      { name: 'honeymoon_start_date', label: 'Start Date', type: 'date', required: true },
      { name: 'honeymoon_end_date', label: 'End Date', type: 'date', required: true },
      { name: 'honeymoon_couple_name', label: 'Couple Names', type: 'text', placeholder: 'John & Jane', required: true },
      { name: 'honeymoon_special_requests', label: 'Special Requests', type: 'textarea', placeholder: 'Romantic dinner, spa, etc.', required: false },
      { name: 'honeymoon_budget', label: 'Budget Range', type: 'select', options: ['Mid-range (€2000-5000)', 'Luxury (€5000+)', 'Ultra Luxury (€10000+)'], required: true }
    ],
    submitLabel: 'Create Honeymoon Package',
    nextAction: 'holidaySummary'
  },
  
  holidayFamilyModal: {
    action: 'showForm',
    message: '👨‍👩‍👧‍👦 Family Trip Package Form',
    fields: generalInfoFields,
    submitLabel: 'Create Family Package',
    nextAction: 'holidaySummary'
  },
  
  holidaySummary: {
    type: 'summary',
    message: '✨ We\'ll create a customized holiday plan for you!\n\nStay tuned...',
    buttons: [
      { label: '📩 Get Itinerary', action: 'holidayItinerary' },
      { label: '💰 Get Package Price', action: 'holidayPrice' },
      { label: '❓ Holiday FAQ', action: 'holidayFAQ' },
      { label: '📞 Contact Us', action: 'callSupport' }
    ]
  },
  
  holidayItinerary: {
    message: '📅 Your Custom Itinerary\n\n✨ We\'re preparing a detailed day-by-day itinerary for you including:\n• Hotel recommendations\n• Activity suggestions\n• Transportation tips\n• Restaurant picks\n• Budget breakdown\n\nCheck your email shortly! 📧',
    buttons: [
      { label: '💰 Get Price', action: 'holidayPrice' },
      { label: '❓ FAQ', action: 'holidayFAQ' },
      { label: '📞 Contact Us', action: 'callSupport' }
    ]
  },
  
  holidayPrice: {
    message: '💰 Package Pricing\n\n• Budget: €800-1500 per person\n• Mid-range: €1500-3000 per person\n• Luxury: €3000+ per person\n\nIncludes flights, hotels, activities!\n\nWant a custom quote?',
    buttons: [
      { label: '❓ FAQ', action: 'holidayFAQ' },
      { label: '📞 Contact Us', action: 'callSupport' },
      { label: '📝 Book Package', action: 'holidayBook' }
    ]
  },
  
  holidayBook: {
    message: '🎉 Holiday package booked!\n\nOur travel experts will contact you within 24 hours with confirmation and detailed itinerary.',
    buttons: [
      { label: '📦 New Package', action: 'holidayPackages' },
      { label: '❌ End Chat', action: 'endChat' }
    ]
  },
  
  callSupport: {
    message: '📞 Contact Us\n\nPhone: +1-800-VISA-NOW\nEmail: support@schengenvisas.com\nWhatsApp: Click the button below\n\nAvailable 24/7! 🌍',
    buttons: [
      { label: '💬 WhatsApp Us', action: 'whatsappChat' },
      { label: '📧 Email Us', action: 'emailForm' }
    ]
  },
  
  whatsappChat: {
    message: '💬 WhatsApp activated!\n\nYou\'ll be connected to our team. Redirecting...',
    buttons: [
      { label: '↩️ Back to Chat', action: 'visaServices' }
    ]
  },
  
  emailForm: {
    action: 'showForm',
    message: '📧 Send us an Email',
    fields: [
      ...generalInfoFields.slice(0, 4),
      { name: 'subject', label: 'Subject', type: 'text', placeholder: 'e.g., Visa Query, Booking Issue', required: true },
      { name: 'message', label: 'Your Message', type: 'textarea', placeholder: 'Type your message here...', required: true, rows: 4 }
    ],
    submitLabel: 'Send Email',
    nextAction: 'emailConfirm'
  },
  
  emailConfirm: {
    message: '✅ Email sent!\n\nWe\'ll respond within 2 hours.\n\nThank you! 🙏',
    buttons: [
      { label: '🛂 Apply for Visa', action: 'visaFormModal' },
      { label: '❌ End Chat', action: 'endChat' }
    ]
  },
  
  endChat: {
    message: '👋 Thank you for chatting with us!\n\nWe hope to serve you soon. Have a great day! 🌟',
    buttons: [
      { label: '💬 Start Over', action: 'greeting' }
    ]
  },

  resetGreeting: {
        message: 'Hello 👋\n\nWelcome to SchengenVisaItinerary\n\nHow can we help you today?',
        buttons: [
            { label: '🛂 Visa Services', action: 'visaServices' },
            { label: '📋 Travel Documentation for Visa Process', action: 'travelDocsForVisa' },
            { label: '🏖️ Holiday Packages', action: 'holidayPackages' }
        ]
    }
};