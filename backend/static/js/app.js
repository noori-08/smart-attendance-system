async function studentLogin(){

    let r = document.getElementById('result');

    let email =
        document.getElementById('email').value.trim();

    let password =
        document.getElementById('password').value;


    if(!email || !password){

        r.textContent =
            'Enter your email and password.';

        return;
    }


    let x = await fetch('/login', {

        method: 'POST',

        headers: {
            'Content-Type': 'application/json'
        },

        body: JSON.stringify({
            email: email,
            password: password
        })

    });


    let d = await x.json();


    r.textContent =
        d.message || '';


    if(d.success)
        location.href = '/dashboard';
}


async function teacherLogin(){
    let r=document.getElementById('result');

    let x=await fetch('/teacher_login',{
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({
            email:email.value.trim(),
            password:password.value
        })
    });

    let d=await x.json();

    r.textContent=d.message||'';

    if(d.success)
        location.href='/teacher_dashboard';
}


async function generateQR(){

    let r =
        document.getElementById('result');

    let countdown =
        document.getElementById('qrCountdown');

    let x =
        await fetch('/generate_qr', {

            method: 'POST',

            headers: {
                'Content-Type': 'application/json'
            },

            body: JSON.stringify({
                offering_id:
                    document.getElementById('subject').value
            })

        });


    let d =
        await x.json();


    r.textContent =
        d.message;


    if(d.success){

        let q =
            document.getElementById('qr');

        q.style.display =
            'block';

        q.src =
            '/static/qr_codes/current_qr.png?t='
            + Date.now();


        // ======================================
        // QR COUNTDOWN
        // ======================================

        let expiryTime =
            new Date(d.expires_at).getTime();


        function updateQRCountdown(){

            let now =
                new Date().getTime();

            let remaining =
                expiryTime - now;


            if(remaining <= 0){

                countdown.textContent =
                    '🔴 QR EXPIRED';

                countdown.style.color =
                    '#ff4d6d';

                clearInterval(
                    qrCountdownInterval
                );

                return;
            }


            let totalSeconds =
                Math.floor(
                    remaining / 1000
                );


            let minutes =
                Math.floor(
                    totalSeconds / 60
                );


            let seconds =
                totalSeconds % 60;


            countdown.textContent =
                'QR expires in ' +
                String(minutes).padStart(2, '0') +
                ':' +
                String(seconds).padStart(2, '0');


            countdown.style.color =
                '#ffffff';
        }


        updateQRCountdown();


        if(window.qrCountdownInterval){

            clearInterval(
                window.qrCountdownInterval
            );
        }


        window.qrCountdownInterval =
            setInterval(
                updateQRCountdown,
                1000
            );
    }
}

function togglePassword(){

    const password =
        document.getElementById("password");

    const button =
        document.querySelector(".password-toggle");

    if(password.type === "password"){

        password.type = "text";

        button.innerHTML = `
            <svg
                class="eye-icon"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
            >
                <path d="M3 3l18 18"/>
                <path d="M10.6 10.6a2 2 0 0 0 2.8 2.8"/>
                <path d="M9.9 5.1A10.8 10.8 0 0 1 12 5c7 0 10 7 10 7a18.5 18.5 0 0 1-3.1 4.4"/>
                <path d="M6.6 6.6C3.8 8.5 2 12 2 12s3.5 7 10 7a10.8 10.8 0 0 0 4.1-.8"/>
            </svg>
        `;

        button.setAttribute(
            "aria-label",
            "Hide password"
        );

    } else {

        password.type = "password";

        button.innerHTML = `
            <svg
                class="eye-icon"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
            >
                <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"/>
                <circle cx="12" cy="12" r="3"/>
            </svg>
        `;

        button.setAttribute(
            "aria-label",
            "Show password"
        );
    }
}

// ==========================================
// TEACHER - LOAD ENROLLMENT STUDENTS
// ==========================================

async function loadEnrollmentStudents(){

    const offeringId =
        document.getElementById(
            "enrollmentOffering"
        ).value;

    const container =
        document.getElementById(
            "enrollmentStudents"
        );

    const message =
        document.getElementById(
            "enrollmentMessage"
        );

    container.innerHTML = "";
    message.textContent = "";

    if(!offeringId){
        return;
    }

    container.innerHTML =
        "<p>Loading students...</p>";

    try{

        const response =
            await fetch(
                "/offering_students?offering_id="
                + offeringId
            );

        const data =
            await response.json();

        if(!data.success){

            container.innerHTML = "";

            message.textContent =
                data.message ||
                "Could not load students.";

            return;
        }

        if(data.students.length === 0){

            container.innerHTML =
                "<p>No students found for this class.</p>";

            return;
        }

        let html = `
            <div style="overflow-x:auto;">

                <table style="width:100%;">

                    <thead>

                        <tr>
                            <th>Name</th>
                            <th>USN</th>
                            <th>Email</th>
                            <th>Status</th>
                            <th>Action</th>
                        </tr>

                    </thead>

                    <tbody>
        `;

        data.students.forEach(student => {

            const enrolled =
                student.enrolled == 1;

            html += `
                <tr>

                    <td>
                        ${student.name}
                    </td>

                    <td>
                        ${student.usn}
                    </td>

                    <td>
                        ${student.email}
                    </td>

                    <td>
                        ${
                            enrolled
                            ? "Enrolled"
                            : "Not Enrolled"
                        }
                    </td>

                    <td>

                        <button
                            onclick="updateEnrollment(
                                ${student.student_id},
                                ${offeringId},
                                '${enrolled ? "remove" : "enroll"}'
                            )"
                        >
                            ${
                                enrolled
                                ? "Remove"
                                : "Enroll"
                            }
                        </button>

                    </td>

                </tr>
            `;
        });

        html += `
                    </tbody>

                </table>

            </div>
        `;

        container.innerHTML = html;

    }
    catch(error){

        console.error(
            "Enrollment error:",
            error
        );

        container.innerHTML = "";

        message.textContent =
            "Could not load students.";
    }
}


// ==========================================
// TEACHER - ENROLL / REMOVE STUDENT
// ==========================================

async function updateEnrollment(
    studentId,
    offeringId,
    action
){

    try{

        let url;

        if(action === "remove"){

            url =
                "/remove_student_from_offering";

        } else {

            url =
                "/enroll_student";

        }


        const response =
            await fetch(
                url,
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify({

                        student_id:
                            studentId,

                        offering_id:
                            offeringId

                    })
                }
            );


        const data =
            await response.json();


        const message =
            document.getElementById(
                "enrollmentMessage"
            );


        message.textContent =
            data.message || "";


        if(data.success){

            await loadEnrollmentStudents();

        }

    }

    catch(error){

        console.error(
            "Enrollment update error:",
            error
        );


        document.getElementById(
            "enrollmentMessage"
        ).textContent =
            "Could not update enrollment.";
    }

}

// ==========================================
// CLASS OFFERING - LOAD SUBJECTS
// ==========================================

// ==========================================
// LOAD SUBJECTS FOR CLASS OFFERING
// ==========================================

async function loadOfferingSubjects() {

    const select =
        document.getElementById(
            "offeringSubject"
        );

    if (!select) {
        return;
    }

    try {

        const response =
            await fetch(
                "/get_subjects"
            );

        const data =
            await response.json();

        if (!data.success) {

            console.error(
                data.message
            );

            return;
        }

        select.innerHTML =
            '<option value="">Select Subject</option>';

        data.subjects.forEach(
            subject => {

                const option =
                    document.createElement(
                        "option"
                    );

                option.value =
                    subject.subject_id;

                option.textContent =
                    subject.subject_name;

                select.appendChild(
                    option
                );

            }
        );

    } catch (error) {

        console.error(
            "Subject loading error:",
            error
        );

    }
}


// ==========================================
// LOAD ATTENDANCE
// ==========================================

async function loadTeacherAttendance() {

    const box =
        document.getElementById(
            "teacherAttendance"
        );

    if (!box) {
        return;
    }

    const offeringElement =
        document.getElementById(
            "attendanceSubject"
        ) ||
        document.getElementById(
            "attendanceOffering"
        );

    const dateElement =
        document.getElementById(
            "attendanceDate"
        );

    const searchElement =
        document.getElementById(
            "attendanceSearch"
        );

    const offeringId =
        offeringElement
            ? offeringElement.value
            : "";

    const date =
        dateElement
            ? dateElement.value
            : "";

    const search =
        searchElement
            ? searchElement.value.trim()
            : "";

    if (!offeringId) {

        box.innerHTML = `
            <p>
                Please select a class first.
            </p>
        `;

        updateAttendanceCards([]);

        return;
    }

    box.innerHTML =
        "<p>Loading attendance...</p>";

    try {

        const params =
            new URLSearchParams();

        params.append(
            "offering_id",
            offeringId
        );

        if (date) {

            params.append(
                "date",
                date
            );

        }

        if (search) {

            params.append(
                "search",
                search
            );

        }

        const response =
            await fetch(
                "/teacher_attendance?" +
                params.toString()
            );

        const data =
            await response.json();

        if (!data.success) {

            box.innerHTML = `
                <p>
                    ${
                        data.message ||
                        "Could not load attendance."
                    }
                </p>
            `;

            updateAttendanceCards([]);

            return;
        }

        const rows =
            data.attendance || [];

        updateAttendanceCards(
            rows
        );

        if (rows.length === 0) {

            box.innerHTML = `
                <div class="empty-state">

                    <h3>
                        No students found
                    </h3>

                    <p>
                        No students are enrolled
                        in this class.
                    </p>

                </div>
            `;

            return;
        }

        let html = `

            <div
                style="overflow-x:auto;"
            >

                <table
                    style="width:100%;"
                >

                    <thead>

                        <tr>

                            <th>Name</th>

                            <th>USN</th>

                            <th>Subject</th>

                            <th>Date</th>

                            <th>Time</th>

                            <th>Status</th>

                            <th>Classes Taken</th>

                            <th>Classes Attended</th>

                            <th>Attendance %</th>

                        </tr>

                    </thead>

                    <tbody>

        `;

        rows.forEach(
            row => {

                const statusClass =
                    row.status === "Present"
                        ? "status-present"
                        : "status-absent";

                html += `

                    <tr>

                        <td>
                            ${row.name}
                        </td>

                        <td>
                            ${row.usn}
                        </td>

                        <td>
                            ${row.subject_name}
                        </td>

                        <td>
                            ${row.attendance_date}
                        </td>

                        <td>
                            ${row.attendance_time}
                        </td>

                        <td>

                            <span
                                class="${statusClass}"
                            >
                                ${row.status}
                            </span>

                        </td>

                        <td>
                            ${row.classes_taken}
                        </td>

                        <td>
                            ${row.classes_attended}
                        </td>

                        <td>
                            ${row.attendance_percentage}%
                        </td>

                    </tr>

                `;

            }
        );

        html += `

                    </tbody>

                </table>

            </div>

        `;

        box.innerHTML =
            html;

    } catch (error) {

        console.error(
            "Attendance error:",
            error
        );

        box.innerHTML = `
            <p>
                Could not load attendance.
            </p>
        `;

        updateAttendanceCards([]);

    }
}


// ==========================================
// ATTENDANCE SUMMARY
// ==========================================

function updateAttendanceCards(rows) {

    const total =
        rows.length;

    const present =
        rows.filter(
            row =>
                row.status ===
                "Present"
        ).length;

    const absent =
        rows.filter(
            row =>
                row.status ===
                "Absent"
        ).length;

    const rate =
        total > 0
            ? Math.round(
                (
                    present /
                    total
                ) * 100
            )
            : 0;

    const totalElement =
        document.getElementById(
            "totalStudents"
        );

    const presentElement =
        document.getElementById(
            "presentCount"
        );

    const absentElement =
        document.getElementById(
            "absentCount"
        );

    const rateElement =
        document.getElementById(
            "attendanceRate"
        );

    if (totalElement) {

        totalElement.textContent =
            total;

    }

    if (presentElement) {

        presentElement.textContent =
            present;

    }

    if (absentElement) {

        absentElement.textContent =
            absent;

    }

    if (rateElement) {

        rateElement.textContent =
            rate + "%";

    }
}


// ==========================================
// APPLY FILTERS
// ==========================================

async function applyAttendanceFilters() {

    await loadTeacherAttendance();

}


// ==========================================
// CLEAR FILTERS
// ==========================================

function clearAttendanceFilters() {

    const search =
        document.getElementById(
            "attendanceSearch"
        );

    const subject =
        document.getElementById(
            "attendanceSubject"
        );

    const offering =
        document.getElementById(
            "attendanceOffering"
        );

    const date =
        document.getElementById(
            "attendanceDate"
        );

    if (search) {
        search.value = "";
    }

    if (subject) {
        subject.value = "";
    }

    if (offering) {
        offering.value = "";
    }

    if (date) {
        date.value = "";
    }

    const box =
        document.getElementById(
            "teacherAttendance"
        );

    if (box) {

        box.innerHTML =
            "<p>Please select a class first.</p>";

    }

    updateAttendanceCards([]);

}


// ==========================================
// EXPORT CSV
// ==========================================

function exportAttendance() {

    const offeringElement =
        document.getElementById(
            "attendanceSubject"
        ) ||
        document.getElementById(
            "attendanceOffering"
        );

    const dateElement =
        document.getElementById(
            "attendanceDate"
        );

    const searchElement =
        document.getElementById(
            "attendanceSearch"
        );

    const offeringId =
        offeringElement
            ? offeringElement.value
            : "";

    const date =
        dateElement
            ? dateElement.value
            : "";

    const search =
        searchElement
            ? searchElement.value.trim()
            : "";

    if (!offeringId) {

        alert(
            "Please select a class first."
        );

        return;
    }

    const params =
        new URLSearchParams();

    params.append(
        "offering_id",
        offeringId
    );

    if (date) {

        params.append(
            "date",
            date
        );

    }

    if (search) {

        params.append(
            "search",
            search
        );

    }

    window.location.href =
        "/export_attendance?" +
        params.toString();

}


// ==========================================
// PAGE LOAD
// ==========================================

document.addEventListener(
    "DOMContentLoaded",
    function () {

        loadOfferingSubjects();

    }
);