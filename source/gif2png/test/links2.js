// Peter Gale's example, with ducks.gif substituted for clear.gif
  var lOpen = "<A HREF=\"";
  var lSpan = "\"><SPAN CLASS=\"";
  var lEnd  = "</SPAN></A><BR>\n";

  var links = new Array(
	"index.html",	"Main",
//	"javascript:SyllabusAlert()",	"Syllabus",
	"2430_Syllabus_1999_Fall.pdf", "Syllabus (pdf)",
	"2430_Syllabus_1999_Fall.ps", "Syllabus (ps)",
	"policies.html",	"Policies",
	"policies.html#FAQ",	"FAQ",
	"grades_2430.html",	"Grades",
//	"javascript:GradesAlert()",	"Grades",
	"news://csisnet5.uvsc.edu/uvsc.csis.2430",	"NewsGroup",
	"http://csisnet5.uvsc.edu/CSIS2430.html",	"ListServer",
	"UVSCmail.html",	"UVSC Mail",
	"http://www.aw.com/cseng/titles/0-201-32553-5/website/index.html",	"Companion Site",
	"/jargon/",	"The Jargon File",
	"All_Assignments.html",	"All Assignments",
	"Assignment_01.html",	"Assignment 1",
	"All_Assignments.html#Assignment_02",	"Assignment 2",
	"All_Assignments.html#Assignment_03",	"Assignment 3",
	"Assignment_04.html",	"Assignment 4",
	"Assignment_05.html",	"Assignment 5",
	"Assignment_06.html",	"Assignment 6",
	"Assignment_07.html",	"Assignment 7",
	"Assignment_08.html",	"Assignment 8",
	"Assignment_09.html",	"Assignment 9",
	"All_Assignments.html#Assignment_10",	"Assignment 10",
	"All_Assignments.html#Assignment_11",	"Assignment 11",
	"Assignment_12.html",	"Assignment 12",
	"Final_Project.html",	"Final Project");
  
  document.write("<SPAN CLASS=\"link1\"><B>Links</B></SPAN><BR><BR>");
  for ( i = 0 ; i < links.length ; i++ )
  {
	if ( linkName == links[i+1] ) {
	   document.write("\t",lOpen,links[i],lSpan,"linkc\">",links[i+1],lEnd);
	}
	else {
	   document.write("\t",lOpen,links[i],lSpan,"links\">",links[i+1],lEnd);
	}
	
	if ( links[i+1] == "Grades" ) {
	   document.write("\t<BR><P>\n");
	}
	if ( links[i+1] == "The Jargon File" ) {
	   document.write("\t<P>\n");
	}
	i++;
  }
  document.write("\t<img src=\"ducks.gif\" height=\"1\" width=\"115\" ALT=\"\"><BR>\n");
