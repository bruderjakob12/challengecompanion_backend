 // definitions of the required functions
 const fillTimezoneList = () => {

	const timezones = Intl.supportedValuesOf('timeZone');
	const clientTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone;

	const timezoneDropdown = document.getElementById("timezone");
	for (let index = 0; index < timezones.length; index++) {
		const tempOption = document.createElement("option");
		tempOption.value = timezones[index];
		tempOption.innerText = `${timezones[index]}`;
		if (clientTimezone === timezones[index]) {
			tempOption.selected = true;
		}
		timezoneDropdown.appendChild(tempOption);
	}
};

const doSelectedDatesHaveErrors = () => {
	const dateStartInput = document.getElementById("startDate");
	const dateEndInput = document.getElementById("endDate");
	const dateErrorOutput = document.getElementById("dateErrorInfo");
	dateErrorOutput.innerText = "";

	let startMissing = false;
	if (dateStartInput.value === "") {
		startMissing = true;
		dateStartInput.classList.add("inputError");
	} else {
		dateStartInput.classList.remove("inputError");
	}
	let endMissing = false;
	if (dateEndInput.value === "") {
		endMissing = true;
		dateEndInput.classList.add("inputError");
	} else {
		dateEndInput.classList.remove("inputError");
	}
	if (startMissing || endMissing) {
		// do not continue on error - ToDo: make this visible to the user
		dateErrorOutput.innerText = "Missing dates: start and / or end of challenge. Please make sure you have selected one.";
		return true;
	}

	let startIsDate = true;
	let startTimestamp = "";
	try {
		startTimestamp = Date.parse(dateStartInput.value);
	} catch (error) {
		startIsDate = false;
		dateStartInput.classList.add("inputError");
	}

	let endIsDate = true;
	let endTimestamp = "";
	try {
		endTimestamp = Date.parse(dateEndInput.value);
	} catch (error) {
		endIsDate = false;
		dateEndInput.classList.add("inputError");
	}

	if (!startIsDate || !endIsDate) {
		dateErrorOutput.innerText = "Ivalid dates: start and / or end of challenge are not valid dates. Please use yyyy-mm-dd format in case you have no date picker support in your browser...";
		return true;
	}

	const today = new Date();
	const dd = String(today.getDate()).padStart(2, '0');
	const mm = String(today.getMonth() + 1).padStart(2, '0');
	const yyyy = today.getFullYear();

	if (startTimestamp <= new Date(`${yyyy}-${mm}-${dd}`)) {
		dateErrorOutput.innerText = "Ivalid dates: The challenge needs to start in the future...";
		dateStartInput.classList.add("inputError");
		return true;
	}

	if (startTimestamp >= endTimestamp) {
		dateErrorOutput.innerText = "Ivalid dates: The challenge must be longer then one day, please make sure that the end date is bigger then the start date...";
		return true;
	}

	// ToDo: make sure nothing is in the past

	return false;
};

const submitButtonClickHandler = (event) => {
	
	const dateError = doSelectedDatesHaveErrors();
	if (dateError) { return; }

	const dialogElement = document.getElementById("challengeCreationConfirmationDialog");
	const dialogConfigElement = document.getElementById("challengeConfigSummary");

	dialogConfigElement.innerText = "This will be filled dynamically later";

	// dialogElement.addEventListener("close", (e) => {
	// 	console.log(dialogElement.returnValue);
	// });

	dialogElement.showModal();
	// dialogCancelButton.focus();

	// ToDo: make sure it can be closed



};

const dialogCancelClickHandler = (event) => {
	const dialogElement = document.getElementById("challengeCreationConfirmationDialog");
	event.preventDefault(); // We don't want to submit this fake form
  dialogElement.close('cancel'); // Have to send the select box value here.
}

const dialogConfirmClickHandler = (event) => {
	const dialogElement = document.getElementById("challengeCreationConfirmationDialog");
	event.preventDefault(); // We don't want to submit this fake form
  dialogElement.close('send'); // Have to send the select box value here.
}

