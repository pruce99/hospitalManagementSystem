import React, { useState } from "react";
import Button from "react-bootstrap/Button";
import Form from "react-bootstrap/Form";
import Dropdown from "react-bootstrap/Dropdown";
import "bootstrap/dist/css/bootstrap.min.css";
import "./FormComponent.scss";
import axios from "axios";

export default function FormComponent() {
  const [firstName, getFirstName] = useState("");
  const [lastName, getLastName] = useState("");
  const [age, getAge] = useState("");
  const [gender, getGender] = useState("Gender");
  const [phoneNumber, getPhoneNumber] = useState("");
  const [email, getEmail] = useState("");
  const [dep, getDep] = useState("Department");



  const handleChange = (event) => {
    event.preventDefault();
    let objectMap = {};
    objectMap["first_name"] = firstName;
    objectMap["last_name"] = lastName;
    objectMap["age"] = age;
    objectMap["phone_number"] = phoneNumber;
    objectMap["email"] = email;
    objectMap["department"] = dep;
    objectMap["gender"] = gender;

    axios
      .post(`http://localhost:8000/MainApp/patient_info/`, objectMap)
      .then((res) => {
        window.alert("Sucessfully done");
      });
  };

  return (
    <div className="formComponent">
      <div className="form-heading">
        <h1>Patient Details</h1>
      </div>
      <div className="form-body">
        <Form>
          <Form.Group className="mb-3" controlId="formBasicEmail">
            <Form.Label>
              <h5>First Name</h5>
            </Form.Label>
            <Form.Control
              defaultValue={firstName}
              onChange={(event) => getFirstName(event.target.value)}
              type="email"
              placeholder="Enter name"
            />
          </Form.Group>
          <Form.Group className="mb-3" controlId="formBasicEmail">
            <Form.Label>
              <h5>Last Name</h5>
            </Form.Label>
            <Form.Control
              defaultValue={lastName}
              onChange={(event) => getLastName(event.target.value)}
              type="email"
              placeholder="Enter name"
            />
          </Form.Group>

          <Form.Group className="mb-3" controlId="formBasicPassword">
            <Form.Label>
              <h5>Age</h5>
            </Form.Label>
            <Form.Control
              defaultValue={age}
              onChange={(event) => getAge(event.target.value)}
              type="text"
              placeholder="Enter age"
            />
          </Form.Group>

          <div className="dropDown">
            <Dropdown>
              <Dropdown.Toggle variant="secondary" id="dropdown-basic">
                {gender}
              </Dropdown.Toggle>

              <Dropdown.Menu>
                <Dropdown.Item onClick={() => getGender("Male")}>
                  Male
                </Dropdown.Item>
                <Dropdown.Item onClick={() => getGender("Female")}>
                  Female
                </Dropdown.Item>
              </Dropdown.Menu>
            </Dropdown>
          </div>

          <Form.Group className="mb-3" controlId="formBasicPassword">
            <Form.Label>
              <h5>Phone number</h5>
            </Form.Label>
            <Form.Control
              defaultValue={phoneNumber}
              onChange={(event) => getPhoneNumber(event.target.value)}
              type="text"
              placeholder="Enter phone number"
            />
          </Form.Group>

          <Form.Group className="mb-3" controlId="formBasicPassword">
            <Form.Label>
              <h5>Email</h5>
            </Form.Label>
            <Form.Control
            defaultValue={email}
              onChange={(event) => getEmail(event.target.value)}
              type="text"
              placeholder="Enter email"
            />
          </Form.Group>
          <div className="dropDown">
            <Dropdown>
              <Dropdown.Toggle variant="secondary" id="dropdown-basic">
                {dep}
              </Dropdown.Toggle>

              <Dropdown.Menu>
                <Dropdown.Item onClick={() => getDep("ENT")}>ENT</Dropdown.Item>
                <Dropdown.Item onClick={() => getDep("Cardiology")}>
                  Cardiology
                </Dropdown.Item>
                <Dropdown.Item onClick={() => getDep("Pediatrics")}>
                  Pediatrics
                </Dropdown.Item>
                <Dropdown.Item onClick={() => getDep("Orthopedics")}>
                  Orthopedics
                </Dropdown.Item>
              </Dropdown.Menu>
            </Dropdown>
          </div>

          {/* <Form.Group className="mb-3" controlId="formBasicCheckbox">
            <Form.Check type="checkbox" label="Check me out" />
          </Form.Group> */}

          <Button onClick={handleChange} variant="primary" type="submit">
            Submit
          </Button>
        </Form>
      </div>
    </div>
  );
}
